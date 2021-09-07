from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


class WebhookProcessorException(Exception):
    pass


# Class to process the payload key-values to ensure the required values are present before the
# app continues to service the request
class WebhookProcessor:
    def __init__(self, webhook_json):
        self.webhook_json = webhook_json
        # Github Enterprise webhook payload processor

    def checksuite_processor(self):
        try:
            check_type = self.webhook_json["action"]
            if check_type != "rerequested":
                return False
            check_number = self.webhook_json["check_suite"]["id"]
            head_sha = self.webhook_json["check_suite"]["head_sha"]
            pr_repository_owner = \
                self.webhook_json["repository"]["owner"]["login"]
            pr_repository_name = \
                self.webhook_json["repository"]["name"]
            installation_id = self.webhook_json["installation"]["id"]
            html_url = self.webhook_json['repository']['html_url']
            pr_number = self.webhook_json["check_suite"]["pull_requests"][0]["number"]
        except KeyError as key_error:
            logger.error(f"Error retrieving: {key_error};" +
                         " are you sure this is a Check suite?\n")
            raise WebhookProcessorException(
                f"Error retrieving Check suite field: {key_error};" +
                " are you sure this is a Check Suite?")
        except Exception as e:
            logger.error(f"Error: {e}")
            raise WebhookProcessorException(
                f"Error retrieving key: {e}")

        return True

    def checkrun_processor(self):
        try:
            check_type = self.webhook_json["action"]
            if check_type != "rerequested":
                return False
            check_number = self.webhook_json["check_run"]["id"]
            pr_repository_owner = \
                self.webhook_json["repository"]["owner"]["login"]
            pr_repository_name = \
                self.webhook_json["repository"]["name"]
            installation_id = self.webhook_json["installation"]["id"]
            html_url = self.webhook_json['repository']['html_url']
            pr_number = self.webhook_json["check_run"]["pull_requests"][0]["number"]
        except KeyError as key_error:
            logger.error(f"Error retrieving: {key_error};" +
                         " are you sure this is a Check run?\n")
            raise WebhookProcessorException(
                f"Error retrieving Check run field: {key_error};" +
                " are you sure this is a check run?")
        except Exception as e:
            logger.error(f"Error: {e}")
            raise WebhookProcessorException(
                f"Error retrieving key: {e}")

        return True

    def pr_processor(self):
        try:
            pr_type = self.webhook_json["action"]
            pr_number = self.webhook_json["number"]
            pr_repository_owner = \
                self.webhook_json["repository"]["owner"]["login"]
            pr_repository_name = \
                self.webhook_json["repository"]["name"]
            installation_id = self.webhook_json["installation"]["id"]
            html_url = self.webhook_json['pull_request']['html_url']
        except KeyError as key_error:
            logger.error(f"Error retrieving: {key_error};" +
                         " are you sure this is a pull request?\n")
            raise WebhookProcessorException(
                f"Error retrieving PR field: {key_error};" +
                " are you sure this is a pull request?")
        except Exception as e:
            logger.error(f"Error: {e}")
            raise WebhookProcessorException(
                f"Error retrieving key: {e}")

        if pr_type == "opened" or pr_type == "synchronize" or pr_type == "reopened":
            return True
        else:
            return False

    def pr_closed(self):
        try:
            pr_type = self.webhook_json["action"]
            if pr_type == "closed":
                return True
            else:
                return False
        except KeyError as key_error:
            logger.error(f"Error retrieving: {key_error};" +
                         " are you sure this is a pull request?\n")
            raise WebhookProcessorException(
                f"Error retrieving PR field: {key_error};" +
                " are you sure this is a pull request?")
