from gordon.services.common.secrets_loader import get_secrets
import os


# Configuration to load Pagerduty relevant data used at runtime
class PagerDutyConfig:
    def get_pagerduty_url(self):
        pd_url = os.environ.get("PAGERDUTY_URL")
        return pd_url

    def get_pagerduty_api_token(self):
        _pd_token = get_secrets("SECRET_PAGERDUTY_API_TOKEN")
        pd_token = _pd_token["api_token"]
        return pd_token
