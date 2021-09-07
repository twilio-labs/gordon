from gordon.configurations.slack_config import SlackConfig
from celery.utils.log import get_task_logger
import requests
import json
logger = get_task_logger(__name__)


# Slack channel notification service
class SlackService:
    def send_webhook_message(self, slack_message):
        try:
            message = f"*Gordon Notification:* \n"
            message = message + slack_message
            slack_message = {'text': message}
            webhook = SlackConfig().get_slack_webhook()
            slack_alert_response = requests.post(
                webhook, data=json.dumps(slack_message),
                headers={'Content-Type': 'application/json'})
            if slack_alert_response.status_code != 200:
                logger.error(f"Failed sending alert to slack with "
                             f"status code:"
                             f" {slack_alert_response.status_code}")
        except Exception as e:
            logger.error(f"Failed slack notify: {e}")
