import json
import unittest
import gordon
from unittest import mock
from gordon.services.github.webhook_processor import WebhookProcessorException

with open("tests/fixtures/good_pr.json") as good_pr_file:
    pr_string = good_pr_file.read()
with open("tests/fixtures/bad_pr.json") as bad_pr_file:
    bad_pr_string = bad_pr_file.read()


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.app = gordon.create_app('test')

    def test_healthcheck(self):
        with self.app.test_client() as tc:
            res = tc.get("/api/v1/healthcheck")
            assert res.status_code == 200, "[!] Error hitting /heartbeat"

    @mock.patch('gordon.blueprints.blueprints.handle_webhook')
    @mock.patch('gordon.services.github.github_service.GithubAppService.get_github_app_token')
    @mock.patch('gordon.services.github.github_service.GithubService.initiate_check_run')
    def test_post_good_webhook(self, mock_handle_webhook, mock_app_token, mock_GithubService):
        mock_app_token.return_value = "mock"
        mock_GithubService.return_value = {"mock": "mock"}
        with self.app.test_client() as c:
            response = c.post("/api/v1/validate-aboutyaml",
                              data=json.dumps(pr_string, indent=2),
                              headers={
                                  'X-GitHub-Event': 'pull_request',
                                  'X-Hub-Signature': 'sha1=dc2ff3eb4c5ebb29a01b5a0f101ff8f9cc494172'
                              },
                              content_type='application/json')
            # print(json.dumps(response.json, indent=2))
            self.assertEqual(response.status_code, 200)

    @mock.patch('gordon.blueprints.blueprints.handle_webhook')
    @mock.patch('gordon.services.github.github_service.GithubAppService.get_github_app_token')
    @mock.patch('gordon.services.github.github_service.GithubService.initiate_check_run')
    def test_post_bad_webhook(self, mock_handle_webhook, mock_app_token, mock_GithubService):
        mock_app_token.return_value = "mock"
        mock_GithubService.return_value = {"mock": "mock"}
        with self.app.test_client() as c:
            response = c.post("/api/v1/validate-aboutyaml",
                              data=json.dumps(bad_pr_string, indent=2),
                              headers={
                                  'X-GitHub-Event': 'pull_request',
                                  'X-Hub-Signature': 'sha1=128b6bc196aa4ba280f816f6f02e25f663869142'
                              },
                              content_type='application/json')
            # print(json.dumps(response.json, indent=2))
            self.assertRaises(WebhookProcessorException)
