from github import Github, GithubIntegration
from gordon.configurations.github_config import GithubConfig
from celery.utils.log import get_task_logger
import hashlib
import hmac
import requests
import json
import os

logger = get_task_logger(__name__)


class GithubServiceException(Exception):
    pass


class GithubAppServiceException(Exception):
    pass


class GithubService:
    """Wrapper around PyGithub but also adds functionality"""

    def __init__(self, base_url=None, token=None):
        self.github_base_url = base_url
        self.github_token = token
        try:
            if self.github_base_url is not None:
                connection = Github(
                    base_url=self.github_base_url,
                    login_or_token=self.github_token)
            else:

                connection = Github(
                    login_or_token=self.github_token)
            self.github_connection = connection
        except Exception as e:
            logger.error(f"Failed github connection: {e}")

    # Method to get the latest checkrun status to use for sending slack notifications on a PR close action
    def commit_checkrun_status(self, head_sha, url):
        check_url = url + f"/commits/{head_sha}/check-runs"
        headers = {"Accept": "application/vnd.github.antiope-preview+json",
                   "Authorization": f"token {self.github_token}"}
        # data = json.dumps({"name": "gordon", "head_sha": f"{head_sha}"})

        response = requests.get(check_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get check runs for commit: {check_url}")
            raise GithubServiceException(
                "Could not initiate a check-run on the repository"
            )

    def get_repository(self, repository_name):
        try:
            repo = self.github_connection.get_repo(repository_name)
            return repo
        except Exception as e:
            logger.error(f"Failed to get the repository {repository_name}"
                         f". Full error: {e}")

    @staticmethod
    def get_signature(payload, secret):
        key = bytes(secret, 'utf-8')
        digester = hmac.new(key=key, msg=payload, digestmod=hashlib.sha1)
        digest_signature = digester.hexdigest()
        signature = "sha1=" + digest_signature
        # logger.error(f"Computed signature {signature}")
        return signature

    # Method to initiate a check run on Github which makes the app appear on a pull request
    def initiate_check_run(self, head_sha, check_url):
        check_url = check_url + "/check-runs"
        headers = {"Accept": "application/vnd.github.antiope-preview+json", "Authorization": f"token {self.github_token}"}
        data = json.dumps({"name": "gordon", "head_sha": f"{head_sha}"})

        response = requests.post(check_url, headers=headers, data=data)
        if response.status_code == 201:
            return response.json()
        else:
            logger.error(f"Failed to create check run")
            raise GithubServiceException(
                "Could not initiate a check-run on the repository"
            )

    def post_issue_comment(self, comment, repo_name, pr_number):
        try:
            gh_con = self.github_connection
            repo = gh_con.get_repo(repo_name)
            pr = repo.get_pull(int(pr_number))
            pr.create_issue_comment(comment)
        except Exception as e:
            logger.error(e)

    def update_check_run(self, checks_payload, message, status=None, conclusion=None, conclusion_message=None):
        try:
            check_url = checks_payload["url"]
            headers = {"Accept": "application/vnd.github.antiope-preview+json",
                       "Authorization": f"token {self.github_token}"}
            if status == "in_progress":
                data = json.dumps({"name": "gordon", "status": status})

            elif conclusion is not None:
                data = json.dumps({
                    "name": "gordon",
                    "conclusion": conclusion,
                    "output": {
                        "title": "about.yaml validation",
                        "summary": message
                    }
                })
            else:
                logger.error("Received unsupported update command for check run")
                raise GithubServiceException(
                    "Please provide a supported argument to update the check run"
                )
            response = requests.patch(check_url, headers=headers, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to update check run: {check_url}")
        except Exception as e:
            logger.error(f"Failed to update check run: {e}")

    # Method to validate the signature received from Github to ensure we only process requests from a valid Github app
    @classmethod
    def validate_webhook(cls, webhook_body, webhook_secret, sent_signature):
        computed_signature = GithubService.get_signature(webhook_body,
                                                         webhook_secret)
        if not hmac.compare_digest(sent_signature, computed_signature):
            logger.error(
                f"HMAC comparison of signature failed, raising exception. computed: {computed_signature}")
            raise GithubServiceException(
                "Webhook Signature Did Not Match, Please Check Signature")
        return True


# Class to generate a token for the Github app that can be used to access repositories and update pull requests as needed
class GithubAppService:
    def get_github_app_token(self, base_url, installation_id):
        gh_config = GithubConfig()
        integration_id, pem_key = gh_config.get_github_secrets()
        try:
            git_app_handler = GithubIntegration(integration_id,
                                                pem_key, base_url=base_url)
            access_token = git_app_handler.get_access_token(int(installation_id))
            token = access_token.token
            return token
        except Exception as e:
            logger.error(f"Failed to retrieve git token: {e}")
            raise GithubAppServiceException(
                "Failed to retrieve Github App token"
            )
