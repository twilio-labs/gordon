import os


# Jira configuration loader
class JIRAConfig:
    def get_jira_url(self):
        jira_url = os.environ.get("JIRA_API")
        return jira_url
