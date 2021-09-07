import json
import os
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


class SecretsLoaderException(Exception):
    pass


# Function to load secrets from environment variables containing the path of files containing secrets
def get_secrets(secrets_env_name):
    secrets_filename = os.environ.get(secrets_env_name)

    if secrets_filename is None:
        msg = f"Secrets Filename Env ({secrets_env_name}) " + \
              "not defined, will not be usable"
        logger.error(msg)
        raise SecretsLoaderException(msg)
    elif not os.path.exists(secrets_filename):
        msg = f"Secrets File {secrets_filename} not found"
        logger.error(msg)
        raise SecretsLoaderException(msg)
    else:
        with open(secrets_filename) as secrets_file:
            secrets_json = json.loads(secrets_file.read())
            return secrets_json
