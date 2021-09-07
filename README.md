# Gordon
Gordon is status check Github app to enforce and validate about.yaml file specifications in a repository during pull requests to drive code ownership at scale within an organization.
## Application capabilities:
Service is responsible for:
- Real-time Pull Request processor to check for the presence of about.yaml file and also validate the contents of the file
- Notify the user on the PR checks section about any issues in the about.yaml file in the repository
- Slack notify a team channel when pull requests with invalid about.yaml files have been merged

Service does NOT:
- Create an about.yaml file for the user
- Block pull request merges on check failures

## What is about.yaml?
"about.yaml” is the file specification we came up with to solve our difficulties finding code owners. It’s designed to be included in all repositories company-wide, and all the information we need to track ownership.

As for the naming? The file is essentially talking “about” the codebase and its ownership, hence our choice of “about.yaml”. The YAML specification is extendable and can be modified to fit the needs of any company. We at Twilio use multiple specifications to scale this file to our codebases while leaving it adaptable for when new teams and companies join Twilio.

One about.yaml specification we think would serve as a great example of the power of the paradigm – and also can be widely adopted – is below :

```
version: 1
organization: twilio
jira_id: <jira project id>
pagerduty_id: <pagerduty schedule id>
```
This specification has the following fields
- Version - this can be used for the versioning of the file in case you ever decide you want change the YAML specification and do not want to break any automation tied to specific file formats
- Organization - this field helps identify which organization this file is coming from during automation efforts – useful for if a team joins your company, perhaps through an acquisition. For us, this might allow Twilio, and any child organizations to maintain slightly different formats if needed.
- Jira_id - If you use Jira then you’d add the Jira project ID of the team owning the codebase
- Pagerduty_id - Pagerduty schedule ID of the team owning the codebase which can be used to page the team when there’s an incident on a particular codebase

This file specification is very fluid and can be changed to anything that is relevant to the organization where it’s being implemented.

Note: If you plan on changing the about.yaml file format, then ensure you've updated the schemas used for validation. Schema for the default runs is [here](https://github.com/twilio-labs/gordon/blob/main/gordon/services/validator/default/default_schema.json) and schema for the non-default organizations is [here](https://github.com/twilio-labs/gordon/blob/main/gordon/services/validator/acquisition/acquistion_schema.json).


## How does Gordon work?
Gordon is a Flask-Celery-Redis multi-container application that is installed as a Github app to run on every Pull Request created against the main branch of a repo on which the Github app is installed.

The Flask container is the entry point for the service by exposing API routes defined in blueprints.py. Once a Pull request payload is received on the API route the service forwards the payload to a Redis queue for the Celery container to pick up and
validate for the presense and contents of about.yaml file in the default and commit reference branches. After the celery container scans both the branches for the validity of the file it updates a status check on the pull request.
The Github app is configured with the Flask API URL and a shared secret used for generating the payload SHA checksum.

One way the API URL can be setup is by deploying this code on an host and assigning a application load balancer to this host.

### Creating a Github App
Note: When creating the app please make sure you have a DNS ready for host on which you'll be deploying Gordon containers and a secure secret string for the webhook secret.

Github Admins would need to create and install a Github app on Github before running or deploying the Gordon application.
To know more about creating a Github app please read this [guide](https://docs.github.com/en/free-pro-team@latest/developers/apps/creating-a-github-app)

App Name: gordon (or) choose any name you want in your organization

Webhook URL: http(s)://your-hosted-gordon-dns/api/v1/validate-aboutyaml

To test this locally you can create a ngrok endpoint to feed into your Github app webhook section

### Github App Permissions
For this application to work your Github app will have to enable the following permissions and subscriptions on the permissions page of the Github app:
Repository Permissions:
- Checks: Read & write
- Comments: Read-only
- Metadata: Read-only
- PullRequests: Read & write
- Webhooks: Read & write

All other permissions are left unchanged to the default value of No access

Subscribe to events:
- Pull request
- Check run
- Check suite

Finally click “Create GitHub App”. After successful app creation follow the “generate a private key” link in the top section of the app web page


Once the private key is generated store it in a secure location.
This generated private key is one of the pieces of data used to generate a session token for app interaction.

After generating the private key, install the app on all the orgs you want it to monitor.

## Running Gordon
This is a multi-container application designed to bring up all three containers (Flask, Celery, Redis) via the /bin/run.sh, so running the Dockerfile image should bring up the entirety of the application

### Environment variables:
#### Note: For deployment using docker-compose.yaml populate the these environment variables in [localdev.env](https://github.com/twilio-labs/gordon/blob/main/configuration/environment/localdev.env). If you're deploying this by building and running each container image individually via Dockerfile.api, Dockerfile.celery then the these environment variables are in the respective Dockerfiles
The three variables below are single string values provided by the user
- GITHUB_API: This is the API URL for Github. Eg. if you have your Enterprise Github DNS as https://github.mockcompany.com then your API would be something like https://github.mockcompany.com/api/v3. Or for cloud Github use https://api.github.com
- JIRA_PI: Your company's JIRA server web URL
- PAGERDUTY_URL: API URL for the service to use for validating Pagerduty schedule ids against

The below environment variables load path to files with credentials in them. Load the json file key values in the files available [here](https://github.com/twilio-labs/gordon/tree/main/local_dev_secrets) before running the application.
- SECRET_GITHUB_SECRET: This variable loads github_secrets.json and has the Github app's shared webhook secret, integration ID, and the pem key. All these three secrets are obtained from the Github app settings page.
  
  webhook secret - This is the secret configured during the app creation process
  integration ID - This is the app ID shown on the github app settings page
  pem key - this is the private key generated during the app installation process
- SECRET_SLACK_WEBHOOKS: This loads slack_webhook.json and has the webhook URL to which the gordon app will send slack notifications
- SECRET_AD_USER: This loads ad_user.json and has the username and password for the user ID to access the org's JIRA board
- SECRET_PAGERDUTY_API_TOKEN: This loads pagerduty.json and has the API token needed for validating against the Pagerduty API

Note: If you do not move the JSON secrets files location then you do not need to update the above three environment variables values already present in the Dockerfiles or docker-compose.yaml

### Running/Serving the Docker Image
This command will use docker-compose.yaml to bring up all the containers. Please update configuration/environment/localdev.env with values relevant to your organisation before running the below command
```bash
make serve
```
Once you’ve done this and do not intend to use Dockerfile for serving the application then jump to “Server Healthcheck” section

### Building and running the service using Dockerfiles
There are two ways to build and run the Dockerfiles. There are four Dockerfiles present in the repository, three of which are used to generate an individual image for each container needed for this service to work, and the fourth one is a Dockerfile setup to create a image that can be used to either bring up the Flask application or the celery worker depending on the GORDON_RUN_MODE environment variable value (api or worker) provided

To run any of the steps below you need to be present in the root folder of the repository

Note: Ensure you’ve updated the environment variables in Dockerfile.api and Dockerfile.worker files


#### Building images from individual Dockerfiles
There are three Dockerfiles relevant to this step. Dockerfile.api, Dockerfile.worker, and Dockerfile.redis

###### To build the Flask API image
```
docker build -f Dockerfile.api -t gordon-api:<version> .
```

###### To build the celery image
```
docker build -f Dockerfile.worker -t gordon-worker:<version> .
```

###### To build the redis image
```
docker build -f Dockerfile.redis -t gordon-redis:<version> .
```

#### Running built images
The three images built in the previous steps all run in separate networks due to which they won't be able to talk to each other. To enable inter-container communications we need to add them to a container network

##### Create a docker network
```
docker network create gordon-network
```
Run the images using the created network in the following order:
Start redis container:
```
docker run --net gordon-network --name redis gordon-redis:<version>
```

Start celery container:
```
docker run --net gordon-network gordon-worker:<version>
```

Start Flask API container:
```
docker run --net gordon-network -p 9001:9001 gordon-api:<version>
```

### Building and running a single image for Flask API container and celery worker container
#### This step is useful only if you have a orchestration that allows you to feed in environment variables, secrets and other configurations at deployment time. Please use the above method of running the containers if you don't have a configurable CI/CD setup.
To build a single docker image for bringing up the api and celery worker based on GORDON_RUN_MODE environment variable
```bash
make build
```
This command will also create the redis image that is needed for service

If the built image is run with the environment variable GORDON_RUN_MODE=api, it will bring up the Flask application
If the image is run with environment variable GORDON_RUN_MODE=worker then the celery worker will be initiated

### Server Healthcheck
Now that the API is ready to receive requests navigating to `http://localhost:9001/api/v1/healthcheck` in a browser should return a valid response or you could do a curl
```bash
curl localhost:9001/api/v1/healthcheck
```
Both should show the following message:
`{"healthcheck": "ready"}`

### Running a Pull Request scan
If you have a webhook payload of the Github app for your Pull Request then you can run the following curl command locally to test your application:
```bash
curl -X POST -H "content-type: application/json" -H "X-Hub-Signature: sha1=<signature>" -H "X-GitHub-Event: pull_request" -d @tests/fixtures/good_pr.json http://localhost:9001/api/v1/validate-aboutyaml
```
## Customizing Gordon for your own organization
By default Gordon validates for the YAML specification mentioned above in the README. Say you have a new acquisition tomorrow and want to add a about.yaml file there, but the current specification doesn't fit well into the new acquisition. To facilitate such additions another YAML specification and its verification is defined [here](https://github.com/twilio-labs/gordon/blob/main/gordon/services/validator/acquisition) to serve as an example of how one could add on top of this code base to implement more fields in their about.yaml file and add validation methods for those fields

Ensure you've edited the `organization` values in the acquisition_schema.json file to include the organizations you expect to see in your about.yaml files
