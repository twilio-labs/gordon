import yaml
import base64
import requests
import functools
import json
from gordon.services.validator.default import default_constants
from gordon.configurations.ad_user_config import ADUser
from celery.utils.log import get_task_logger
from jsonschema import Draft7Validator
from github import GithubException, GithubObject

logger = get_task_logger(__name__)


@functools.lru_cache(maxsize=1)
def get_auth():
    ad = ADUser()
    _username, _password = ad.get_ad_creds()
    return _username, _password


class AboutYamlException(Exception):
    pass


# Class to validate the schema of the about.yaml file and also the contents of the fields
class AboutYaml:
    def __init__(self, repo, ref=GithubObject.NotSet):
        self.data = None
        self.version = None
        self.load(repo, ref)

    def __bool__(self):
        return self.data is not None

    def load(self, repo, ref):
        try:
            contents = repo.get_contents("about.yaml", ref=ref)
            data = base64.b64decode(contents.content).decode()
            self.data = yaml.load(data, Loader=yaml.FullLoader)
            return self.is_valid
        except GithubException as e:
            self.data = None
            logger.debug(f"Github exception: {e}")
            return self.is_valid

        except Exception as e:
            msg = "Could not parse about.yaml"

            if ref != GithubObject.NotSet:
                msg += f" from ref={ref}"

            raise AboutYamlException(msg)

    @property
    @functools.lru_cache()
    def is_valid(self):
        if not self.data or "organization" not in self.data:
            return False

        self.version = self.data["organization"]
        return Draft7Validator(default_constants.get_yaml_schema()).is_valid(self.data)

    @property
    @functools.lru_cache()
    def is_valid_jira(self):
        try:
            auth = get_auth()
            endpoint = self.data.get("jira_id")
            url = f"{default_constants.JIRA_BASE_URL}{endpoint}"
            response = requests.get(url, auth=auth)

            if response.status_code == 200:
                result = response.json()

                if result["projectCategory"]["name"] != "Defunct":
                    return True
                else:
                    return False
            elif response.status_code == 404:
                return False
            elif response.status_code == 401:
                logger.error(
                    f"JIRA service user authentication failure with code {response.status_code}.")
                raise AboutYamlException(
                    "JIRA service user auth failure code 401"
                )
            elif response.status_code == 403:
                logger.error(f"Service account blocked on JIRA authentication with status code:"
                             f"{response.status_code} and message: {response.text}")
                raise AboutYamlException(
                    "JIRA service user auth failure"
                )
            else:
                logger.error(f"JIRA server down, with status code:"
                             f"{response.status_code} and message: {response.text}")
                raise AboutYamlException(
                    "JIRA server error"
                )
        except Exception as e:
            logger.error(f"Failed verifying Jira project: {e}")
            raise AboutYamlException(
                "JIRA service user auth failure"
            )

    @property
    def is_valid_pagerduty(self):
        api_url, api_token = default_constants.PAGERDUTY_URL, default_constants.PAGERDUTY_TOKEN
        schedule_id = self.data.get("pagerduty_id")
        pd_url = api_url + f"{schedule_id}/users"
        headers = {'Authorization': f"Token token={api_token}", 'Accept': 'application/vnd.pagerduty+json;version=2'}

        try:
            response = requests.get(pd_url, headers=headers)
            if response.status_code == 200:
                return True

            elif response.status_code == 404:
                return False

            elif response.status_code == 401:
                logger.error(
                    "Failed Pagerduty verification with status code: "
                    f"{response.status_code}, message: {response.text}"
                )
                raise AboutYamlException(
                    "Pagerduty token auth failure code 401"
                )

            else:
                logger.error(
                    "Pagerduty server down with status code: "
                    f"{response.status_code}, message: {response.text}"
                )
                raise AboutYamlException(
                    "Pagerduty server error"
                )

        except Exception as e:
            logger.error(f"Failed verifying Pagerduty data: {pd_url}")
            raise AboutYamlException(
                f"Failed verifying Pagerduty data: {pd_url}"
            )
