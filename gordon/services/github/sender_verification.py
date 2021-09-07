from celery.utils.log import get_task_logger
from gordon.configurations.github_config import GithubConfig
from gordon.services.github.github_service import GithubService, GithubServiceException
logger = get_task_logger(__name__)


class SenderVerificationException(Exception):
    pass


# Class to ensure the payload received via the Github app is consumable and formatted as expected
class SenderVerificationProcessor:
    def __init__(self, event_type, sent_signature, webhook_json):
        self.webhook_json = webhook_json
        self.event_type = event_type
        self.sent_signature = sent_signature
        self.all_check_status = False
        self.check_run = False
        self.gh_config = GithubConfig()
        self.git_wh_secret = self.gh_config.get_github_webhook_secret()

    def verify_sender(self):
        if self.event_type != "pull_request" and self.event_type != "check_run" and self.event_type != "check_suite":
            logger.error(f"Received a unsupported action: {self.event_type}")
            return self.all_check_status, self.event_type

        if self.sent_signature is None:
            logger.error("Missing github signature")
            return self.all_check_status, self.event_type

        try:
            GithubService.validate_webhook(
                webhook_body=self.webhook_json,
                webhook_secret=self.git_wh_secret,
                sent_signature=self.sent_signature
            )
        except GithubServiceException as github_service_exception:
            logger.error(github_service_exception)
            return self.all_check_status, self.event_type

        self.all_check_status = True

        return self.all_check_status, self.event_type
