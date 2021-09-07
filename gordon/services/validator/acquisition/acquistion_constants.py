import os
import json
import functools

from gordon.configurations.jira_config import JIRAConfig
from gordon.configurations.pagerduty_config import PagerDutyConfig

# Constants to used in the validation process for both the branches
JIRA_BASE_URL = JIRAConfig().get_jira_url()
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

PAGERDUTY_URL = PagerDutyConfig().get_pagerduty_url()
PAGERDUTY_TOKEN = PagerDutyConfig().get_pagerduty_api_token()


CHECKRUN_CONCLUSIONS = {
    "success": "success",
    "failure": "failure",
    "cancelled": "cancelled"
}


# Raises Exception on file not found
@functools.lru_cache()
def get_yaml_schema():
    with open(os.path.dirname(os.path.realpath(__file__)) + "/acquistion_schema.json", "r") as schema_file:
        YAML_SCHEMA = json.load(schema_file)
        return YAML_SCHEMA
