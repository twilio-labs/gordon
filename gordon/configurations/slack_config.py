from gordon.services.common.secrets_loader import get_secrets
import os


# Configuration for use when Slack interaction is necessary
class SlackConfig:
    def get_slack_webhook(self):
        webhooks = get_secrets("SECRET_SLACK_WEBHOOKS")
        webhook = webhooks["hook"]
        return webhook
