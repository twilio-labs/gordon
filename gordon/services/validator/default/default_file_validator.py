from gordon.services.validator.default.default_about_yaml import AboutYaml, AboutYamlException
from gordon.configurations.github_config import GithubConfig
from gordon.services.github.github_service import GithubService, GithubAppService
from celery.utils.log import get_task_logger
from gordon.services.validator.default import default_constants

logger = get_task_logger(__name__)


class DefaultFileValidator:
    def __init__(self, payload, repo_name, ref_sha, installation_id, pr_number):
        """
        :param payload: Github app payload in Json format
        :param repo_name: Name of repo for which the check is running
        :param ref_sha: SHA value of the commit from which the pull request was generated
        :param installation_id: Github app installation id
        :param pr_number: pull request number for twhich this run was initiated
        """
        self.git_api = GithubConfig().get_github_api()
        self.pr_number = pr_number
        self.payload = payload
        self.repo_name = repo_name
        self.ref_sha = ref_sha
        self.installation_id = installation_id
        self.git_token = self.get_github_token()
        self.main_checkrun_message = "<h2>Check results on main branch:</h2>\n"
        self.ref_checkrun_message = f"<h2>Check results on commit branch {self.ref_sha}</h2>\n"

    # Method called by the celery processor to initiate the about.yaml file validation and update check-run status accordingly
    def check_executor(self):
        git_service = GithubService(self.git_api, self.git_token)
        self.payload = git_service.update_check_run(self.payload, "update stats", status="in_progress")

        try:
            repo = git_service.get_repository(self.repo_name)
            main_file = AboutYaml(repo)
            ref_file = AboutYaml(repo, self.ref_sha)
            """
            check_message_constructor() is a important function as this is what constructs the end message on the
            page of a status check of a pull request. Observe how this method in this file is called twice for each of
            the keys in the yaml file. This is to create output messages for the main and ref branches individually.
            And AboutYaml class is what has the methods used to verify the validity of the information put into these files
            """
            self.check_message_constructor("schema_message", main_file.is_valid, {})
            self.check_message_constructor("schema_message", ref_file.is_valid, {}, ref=True)

            # block 1:- Decision tree to check if file not found in either of the two branches
            if not main_file and not ref_file:
                response = git_service.update_check_run(
                    self.payload,
                    "about.yaml file not found in main or ref branch. Please add an about.yaml file to the repo. "
                    "For more information on about.yaml formats please refer this "
                    "<a href=''>information page</a>",
                    conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])

            # block 2:- Decision tree to check validity of file if found in both main and ref branches
            elif main_file and ref_file:
                # block 2.1:- Scenario where both main and ref files have valid schemas
                if main_file.is_valid and ref_file.is_valid:
                    self.check_message_constructor(
                        "jira_id", main_file.is_valid_jira,
                        {'jira_id': main_file.data["jira_id"]})

                    self.check_message_constructor(
                        "pagerduty_id", main_file.is_valid_pagerduty, {
                            'pagerduty_id': main_file.data["pagerduty_id"]
                        })

                    self.check_message_constructor(
                        "jira_id", ref_file.is_valid_jira, {
                            'jira_id': ref_file.data["jira_id"]
                        }, ref=True)

                    self.check_message_constructor(
                        "pagerduty_id", ref_file.is_valid_pagerduty, {
                            'pagerduty_id': ref_file.data["pagerduty_id"]
                        }, ref=True)

                    # If main branch file has a file with all valid fields, check if ref has invalid fields as the ref
                    # data may invalidate the main branch data once merged
                    if main_file.is_valid_jira and main_file.is_valid_pagerduty:
                        if not ref_file.is_valid_jira or not ref_file.is_valid_pagerduty:
                            response = git_service.update_check_run(
                                self.payload,
                                f"PR has failed about.yaml validation checks. Latest commit {self.ref_sha} invalidates the about.yaml in main branch. "
                                f"{self.ref_checkrun_message}",
                                conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])
                        else:
                            response = git_service.update_check_run(
                                self.payload,
                                "All checks Passed",
                                conclusion=default_constants.CHECKRUN_CONCLUSIONS["success"])

                    # If main branch doesn't have valid data then check if ref is correcting it in the commit
                    elif ref_file.is_valid_jira and ref_file.is_valid_pagerduty:
                        response = git_service.update_check_run(
                            self.payload, "All checks Passed",
                            conclusion=default_constants.CHECKRUN_CONCLUSIONS["success"])

                    # Files in main and ref are not valid about.yaml then fail the check
                    else:
                        response = git_service.update_check_run(
                            self.payload, f"<b>Failed checks</b> in main and ref branches. \n"
                                          f"{self.main_checkrun_message}\n"
                                          f"{self.ref_checkrun_message}",
                            conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])

                # block 2.2:- If main branch schema is valid and ref branch schema is invalid then fail the check as the merge will corrupt the
                # existing valid about.yaml in the main branch
                elif main_file.is_valid and not ref_file.is_valid:

                    response = git_service.update_check_run(
                        self.payload,
                        f"Failed due to schema issues in ref {self.ref_sha}. Please correct "
                        f"the file format before merging: \n{self.ref_checkrun_message}",
                        conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])

                # block 2.3:- If ref branch has a valid schema but main does not, then verify ref branch file info and pass check if
                # valid. Else fail check since it doesn't fix an existing issue in main branch
                elif ref_file.is_valid and not main_file.is_valid:
                    self.check_message_constructor(
                        "", ref_file.is_valid_jira, {
                            'jira_id': ref_file.data["jira_id"]
                        }, ref=True)
                    self.check_message_constructor(
                        "pagerduty_id", ref_file.is_valid_pagerduty, {
                            'pagerduty_id': ref_file.data["pagerduty_id"]
                        }, ref=True)

                    if not ref_file.is_valid_pagerduty or not ref_file.is_valid_jira:
                        response = git_service.update_check_run(
                            self.payload,
                            f"PR has failed about.yaml validation checks. Latest commit {self.ref_sha} does not have a valid about.yaml file. Please address them before "
                            f"you merge: \n{self.ref_checkrun_message}",
                            conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])
                    else:
                        response = git_service.update_check_run(
                            self.payload,
                            f"Main branch about.yaml file has inconsistencies, but the ref branch {self.ref_sha} "
                            f"addresses them\n {self.ref_checkrun_message}\n\n{self.main_checkrun_message}",
                            conclusion=default_constants.CHECKRUN_CONCLUSIONS["success"])

                # block 2.4:- If main and ref do not a valid schema then immediately fail the PR check
                elif not main_file.is_valid and not ref_file.is_valid:
                    response = git_service.update_check_run(
                        self.payload, f"Failed schema checks on main and ref: \n"
                        f"{self.main_checkrun_message} \n\n{self.ref_checkrun_message}",
                        conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])

            # block 3:- File found in main branch but not in ref  branch, then check the main file schema. If passes, then
            # check if file info is valid or not. If valid then pass, else fail the check
            elif main_file and not ref_file:
                try:
                    ref_yaml_deleted = False
                    pr = repo.get_pull(self.pr_number)
                    for pr_file in pr.get_files():
                        if pr_file.filename == "about.yaml":
                            ref_yaml_deleted = True
                    if ref_yaml_deleted:
                        response = git_service.update_check_run(
                            self.payload,
                            "Looks like you're deleting the about.yaml file in the ref branch. Please add an about.yaml file to the repo. "
                            "For more information on about.yaml formats please refer this "
                            "<a href=''>information page</a>",
                            conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])
                    else:
                        response = git_service.update_check_run(
                            self.payload,
                            "All checks passed",
                            conclusion=default_constants.CHECKRUN_CONCLUSIONS["success"])
                except Exception as e:
                    logger.error(f" Exception: {e}")

            # block 4:- If file found in ref branch and not it main branch, then check the ref branch file schema
            # If schema is valid, then check content validity. If valid then pass check, else fail check
            elif ref_file and not main_file:
                if ref_file.is_valid:
                    self.check_message_constructor(
                        "jira_id", ref_file.is_valid_jira, {
                            'jira_id': ref_file.data["jira_id"]
                        }, ref=True)

                    self.check_message_constructor(
                        "pagerduty_id", ref_file.is_valid_pagerduty, {
                            'pagerduty_id': ref_file.data["pagerduty_id"]
                        }, ref=True)

                    if not ref_file.is_valid_jira or not ref_file.is_valid_pagerduty:
                        response = git_service.update_check_run(
                            self.payload,
                            f"PR has failed about.yaml validation checks. Latest commit {self.ref_sha} invalidates the about.yaml in main branch. "
                            "Please correct them before merging to main:<br/><br/>"
                            f"{self.ref_checkrun_message}\n\n{self.main_checkrun_message}",
                            conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])
                    else:
                        response = git_service.update_check_run(
                            self.payload,
                            "All checks Passed",
                            conclusion=default_constants.CHECKRUN_CONCLUSIONS["success"])
                else:
                    response = git_service.update_check_run(
                        self.payload,
                        f"PR has failed about.yaml validation checks. Latest commit {self.ref_sha} has an invalid about.yaml"
                        " Please correct them before merging to main.</br></br>"
                        f"{self.ref_checkrun_message}\n\n{self.main_checkrun_message}",
                        conclusion=default_constants.CHECKRUN_CONCLUSIONS["failure"])
        except AboutYamlException as a:
            self.cancel_checkrun()
            logger.error(f"Failed one or more checks: {a}")

        except Exception as e:
            self.cancel_checkrun()
            logger.error(f"Failed processing contents of {self.repo_name}: {e}")

    def get_github_token(self):
        try:
            git_app = GithubAppService()
            token = git_app.get_github_app_token(self.git_api, self.installation_id)
            return token
        except Exception as e:
            logger.error(f"Failed getting github app token: {e}")

    # Method to cancel a check status in case when exceptions occur at any step of the file validation
    def cancel_checkrun(self):
        try:
            git_service = GithubService(self.git_api, self.git_token)
            response = git_service.update_check_run(
                self.payload,
                "Check cancelled due to processing errors on Gordon. "
                "Reach out to #help-security for questions",
                conclusion="cancelled")
        except Exception as e:
            logger.error(f"Failed cancelling check run: {e}")

    def check_message_constructor(self, identifier, status, data, ref=None):
        """
        :param identifier: used to identify which piece of the about.yaml is this message being constructed for
        :param status: indicator for pass or fail the validation checks on the data provided in about.yaml file
        :param data: the piece of information to be put into the output message
        :param ref: branch ref identifier to identify if the constructed message is for about.yaml file in main or ref branches
        :return:
        """
        try:
            message = "\n"

            if identifier == "schema_message":
                if not status:
                    message += f"<b>Schema check:</b> FAILED. <b>Description:</b> The format of the file is invalid. Expected schema format:\n"
                    with open(default_constants.CURRENT_DIR + f"/valid_scehmas/default.txt") as file:
                        message += file.read()

            elif identifier == "jira_id":
                if not status:
                    message += f"<b>Jira Check:</b> <i>FAILED</i>. <b>Description:</b> {data['jira_id']} is an invalid value. " \
                               f"Please ensure that this value exists"

            elif identifier == "pagerduty_id":
                if not status:
                    message += f"<b>Pagerdurty Check:</b> <i>FAILED</i>. <b>Description:</b> {data['pagerduty_id']} is not a " \
                               f"valid Pagerduty schedule id. Please provide an active and valid Pagerduty schedule ID"

            if ref is not None:
                self.ref_checkrun_message += message
            else:
                self.main_checkrun_message += message
        except Exception as e:
            logger.error(f"Failed constructing output message: {e}")
