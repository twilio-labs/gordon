from gordon.services.common.secrets_loader import get_secrets
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class ADUserException(Exception):
    pass


# These credentials are used to access your Jira server to validate the Jira project ID mentioned in the about.yaml file
class ADUser:
    def get_ad_creds(self):
        _user1_creds = get_secrets("SECRET_AD_USER")
        username = _user1_creds["username"]
        password = _user1_creds["password"]
        return username, password
