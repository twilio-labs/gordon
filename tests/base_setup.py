import unittest
import os
import tempfile
import uuid

from requests.auth import _basic_auth_str


# Define a common test base for starting servers
class BaseAppSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        # Inspired via http://stackoverflow.com/questions/1323455/python-unit-test-with-base-and-sub-class/17696807#17696807
        if cls is not BaseAppSetup and cls.setUp is not BaseAppSetup.setUp:
            orig_setUp = cls.setUp
            def setUpOverride(self, *args, **kwargs):
                BaseAppSetup.setUp(self)
                return orig_setUp(self, *args, **kwargs)
            cls.setUp = setUpOverride

    def add_auth_headers(self, headers={}):
        headers.update({
            "Authorization": _basic_auth_str("mock", "mockpassword")
        })
        return headers

    def add_service_auth_headers(self, headers={}):
        headers.update({
            "X-Service-Authorization":  "mockservicekey"
        })
        return headers

    def setUp(self):
        """Do some custom setup"""
        dbname = '%s.db' % str(uuid.uuid4())
        self.dbpath = os.path.join(tempfile.gettempdir(), dbname)

        os.environ.update(
            {
                "GORDON_CONFIG": "test",
                "SECRET_GITHUB_SECRET": "/tests/test_secrets/github_secrets.json",
                "SECRET_AD_USER": "/tests/test_secrets/ad_user.json",
                "SECRET_PAGERDUTY_API_TOKEN": "/tests/test_secrets/pagerduty.json",
                "SECRET_SLACK_WEBHOOKS": "/tests/test_secrets/slack_webhook.json"
            }
        )
        self.config = {
            'GORDON_CONFIG':'test',
            'JIRA_API': 'https://mock-test-server/jira',
            'DEBUG':True,
            'LOG_LEVEL': "DEBUG",
            'GITHUB_API': 'https://api.github.com',
            'PAGERDUTY_URL': 'https://api.pagerduty.com/schedules/'
        }
        self.test_secrets = {
        }

    @classmethod
    def tearDownClass(cls):
        if cls is BaseAppSetup:
            for name, method in cls._test_methods:
                setattr(cls, name, method)
            cls._test_methods = []

    # executed after each test
    def tearDown(self):
        if os.path.isfile(self.dbpath):
            os.remove(self.dbpath)
