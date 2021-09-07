from gordon import celery
from celery.utils.log import get_task_logger
from gordon.services.github.webhook_processor import WebhookProcessor
from gordon.configurations.github_config import GithubConfig
from gordon.services.github.github_service import GithubService, GithubAppService
from gordon.services.common.slack_notification import SlackService
from gordon.services.validator.default.default_file_validator import DefaultFileValidator
from gordon.services.validator.acquisition.acquisition_file_validator import AcquistionFileValidator
import json
import os

logger = get_task_logger(__name__)


# Main celery function called to split out the tasks based on the event_type and action received on the Github payload
@celery.task
def webhook_async(webhook_json, payload_event):
    try:
        shared_repo = False
        repo_url = webhook_json["repository"]["html_url"]
        github_organisation = webhook_json["repository"]["owner"]["login"]
        private_repo = webhook_json["repository"]["private"]

        # If Github org is in the acquisition list then initiate the acquisition relevant methods defined in
        # gordon/services/validator/acquisition/acquisition_file_validator
        if github_organisation in ["acquisition1", "acquisition2"]:
            if not private_repo:
                pass
            else:
                # Check if the repo received is a shared repo and shouldn't be included in this status check.
                # If yes, then skip the check. Else, continue processing the request
                with open(os.path.dirname(os.path.realpath(__file__)) + "/acquisition_shared_repos.json") as shared_file:
                    shared_json = json.loads(shared_file.read())

                    for name, url in shared_json.items():
                        if url == repo_url or url == repo_url + "/":
                            shared_repo = True
                if not shared_repo:
                    processor(webhook_json, payload_event, github_organisation)

        # Default handler call if the organization need not be filtered for custom acquisition specific checks
        # Defaults to calling methods under gordon/services/validator/default/default_file_validator
        else:
            if not private_repo:
                pass
            else:
                # Check if the repo received is a shared repo and shouldn't be included in this status check.
                # If yes, then skip the check. Else, continue
                with open(os.path.dirname(os.path.realpath(__file__)) + "/default_shared_repos.json") as shared_file:
                    shared_json = json.loads(shared_file.read())

                    for name, url in shared_json.items():
                        if url == repo_url or url == repo_url + "/":
                            shared_repo = True
                if not shared_repo:
                    processor(webhook_json, payload_event, github_organisation)

    except Exception as e:
        logger.error(f" Exception: {e}")


# A method to act as a sorter for the payload event received and take the appropriate action
def processor(webhook_json, payload_event, github_organisation):
    pr_webhook_processor = WebhookProcessor(webhook_json)
    if payload_event == "check_run" and pr_webhook_processor.checkrun_processor():
        checkrun_setup(webhook_json, github_organisation)

    elif payload_event == "check_suite" and pr_webhook_processor.checksuite_processor():
        checksuite_setup(webhook_json, github_organisation)

    elif payload_event == "pull_request":
        if pr_webhook_processor.pr_processor():
            open_pull_request_setup(webhook_json, github_organisation)

        """
        Remove the below section from comments if you want slack notifications for when
        PRs are closed without valid about.yaml files
        """
        # elif pr_webhook_processor.pr_closed():
        #     closed_pull_request_setup(webhook_json, github_organisation)


# This is to initiate process a payload of X-GitHub-Event: check_run header
def checkrun_setup(webhook_json, github_organisation):
    head_sha = webhook_json["check_run"]["head_sha"]
    check_url = webhook_json["repository"]["url"]
    repo_name = webhook_json["repository"]["full_name"]
    install_id = webhook_json["installation"]["id"]
    pr_number = webhook_json["check_run"]["pull_requests"][0]["number"]
    checkrun_payload = create_check_run(head_sha, check_url, install_id)
    run_url = checkrun_payload["html_url"]
    logger.info(f"Processing check run: {run_url}")

    if github_organisation in ["acquisition1", "acquisition2"]:
        file_handler = AcquistionFileValidator(checkrun_payload, repo_name, head_sha, install_id, pr_number)
    else:
        file_handler = DefaultFileValidator(checkrun_payload, repo_name, head_sha, install_id, pr_number)
    file_handler.check_executor()
    logger.info(f"Completed processing check run: {run_url}")


# This is to initiate process a payload of X-GitHub-Event: check_suite header
def checksuite_setup(webhook_json, github_organisation):
    head_sha = webhook_json["check_suite"]["head_sha"]
    check_url = webhook_json["repository"]["url"]
    repo_name = webhook_json["repository"]["full_name"]
    install_id = webhook_json["installation"]["id"]
    suite_url = webhook_json["check_suite"]["url"]
    pr_number = webhook_json["check_suite"]["pull_requests"][0]["number"]
    checkrun_payload = create_check_run(head_sha, check_url, install_id)
    run_url = checkrun_payload["html_url"]
    logger.info(f"Processing check run: {run_url} under the check suite: {suite_url}")

    if github_organisation in ["acquisition1", "acquisition2"]:
        file_handler = AcquistionFileValidator(checkrun_payload, repo_name, head_sha, install_id, pr_number)
    else:
        file_handler = DefaultFileValidator(checkrun_payload, repo_name, head_sha, install_id, pr_number)
    file_handler.check_executor()
    logger.info(f"Completed processing check run: {run_url} under the check suite: {suite_url}")


# This is to initiate process a payload of X-GitHub-Event: pull_request header
def open_pull_request_setup(webhook_json, github_organisation):
    head_sha = webhook_json["pull_request"]["head"]["sha"]
    check_url = webhook_json["pull_request"]["base"]["repo"]["url"]
    repo_name = webhook_json["repository"]["full_name"]
    install_id = webhook_json["installation"]["id"]
    pr_url = webhook_json["pull_request"]["html_url"]
    checkrun_payload = create_check_run(head_sha, check_url, install_id)
    pr_number = webhook_json["number"]
    logger.info(f"Processing PR: {pr_url}")

    if github_organisation in ["acquisition1", "acquisition2"]:
        file_handler = AcquistionFileValidator(checkrun_payload, repo_name, head_sha, install_id, pr_number)
    else:
        file_handler = DefaultFileValidator(checkrun_payload, repo_name, head_sha, install_id, pr_number)
    file_handler.check_executor()
    logger.info(f"Completed processing PR: {pr_url}")


# Method to process closed pull requests and notify a monitored Slack channel of all the repositories with
# an invalid about.yaml file
def closed_pull_request_setup(webhook_json, github_organisation):
    head_sha = webhook_json["pull_request"]["head"]["sha"]
    check_url = webhook_json["pull_request"]["base"]["repo"]["url"]
    install_id = webhook_json["installation"]["id"]
    pr_url = webhook_json["pull_request"]["html_url"]
    gh_app_service = GithubAppService()
    gh_api = GithubConfig().get_github_api()
    git_token = gh_app_service.get_github_app_token(gh_api, install_id)
    logger.info(f"Processing closed action of PR:{pr_url}")
    gh_service = GithubService(gh_api, git_token)
    response = gh_service.commit_checkrun_status(head_sha, check_url)
    try:
        if int(response["total_count"]) > 0:
            for i in range(len(response["check_runs"])):
                check = response["check_runs"][i]
                if check["name"] == "gordon":
                    if check["conclusion"] == "failure":
                        slack = SlackService()
                        slack.send_webhook_message(f"Gordon check failed for closed PR: {pr_url}")
    except Exception as e:
        logger.error(f"Failed handling closed action on PR {pr_url}: {e}")
    logger.info(f"Completed processing PR: {pr_url}")


def create_check_run(head_sha, check_url, install_id):
    gh_app_service = GithubAppService()
    gh_api = GithubConfig().get_github_api()
    git_token = gh_app_service.get_github_app_token(gh_api, install_id)

    gh_service = GithubService(gh_api, git_token)
    checkrun_payload = gh_service.initiate_check_run(head_sha, check_url)
    return checkrun_payload
