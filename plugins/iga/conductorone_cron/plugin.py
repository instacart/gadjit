import base64
import json
import logging
import time
import models
from datetime import datetime, timedelta

from plugins.iga.conductorone_cron.api import ConductorOneAPIClient
from models import BaseGadjitIGAPlugin


class ConductorOneCronPlugin(BaseGadjitIGAPlugin):
    access_token = None
    client = None

    def __init__(self, config):
        super().__init__(config)
        self.client = ConductorOneAPIClient(config)

    def retrieve_requests(self, event):
        access_requests = []

        # Prepare time-related search operators
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(
            hours=16
        )  # cron runs once per minute, adding a few seconds of grace
        created_after = one_minute_ago.strftime("%Y-%m-%dT%H:%M:%SZ")

        task_summaries = self.client.search_tasks(self._get_access_token(), created_after)
        for task_summary in task_summaries:
            access_request = self._prepare_context_objects(self._get_access_token(), task_summary)
            access_requests.append(access_request)

        return access_requests

    def comment_request(self, access_request, comment):
        self.client.comment_task(self._get_access_token(), access_request.id, comment)

    def approve_request(self, access_request):
        self.client.reassign_task(
            self._get_access_token(),
            access_request.id,
            access_request.iga_metadata.get("policy_step_id"),
            self.config.get('reassign_to_user'),
        )

        # Reassignment causes us to move to another step, which we need to get the ID of.
        new_task_policy_step_id = (
            self.client.get_task(self._get_access_token(), access_request.id)
            .get("taskView")
            .get("task", {})
            .get("policy", {})
            .get("current", {})
            .get("id")
        )

        # Send the approval.
        self.client.approve_task(self._get_access_token(), access_request.id, new_task_policy_step_id)

    def deny_request(self, access_request):
        pass

    def _get_access_token(self):
        if not self.access_token or self._is_jwt_expired(self.access_token):
            self.access_token = self.client.authenticate()

        return self.access_token

    def _prepare_context_objects(self, access_token, task_summary):

        # Get information about the entitlement this task is requesting
        _entitlement_api_response = self.client.get_entitlement(
            access_token, task_summary.get("app_id"), task_summary.get("app_entitlement_id")
        )
        _entitlement_members_api_response = self.client.get_entitlement_members(
            access_token, task_summary.get("app_id"), task_summary.get("app_entitlement_id")
        )

        # Initialize the Entitlement object
        entitlement = models.Entitlement(
            id=task_summary.get("app_entitlement_id"),
            parent_app_id=task_summary.get("app_id"),
            name=_entitlement_api_response.get("appEntitlementView", {})
            .get("appEntitlement", {})
            .get("displayName")
            .replace(" Group Member", ""),
            description=_entitlement_api_response.get("appEntitlementView", {})
            .get("appEntitlement", {})
            .get("description"),
            members=_entitlement_members_api_response,
        )

        # Get information about the user who requested this task
        _user_api_response = self.client.get_user(
            access_token, task_summary.get("task_target_user_id")
        )

        # Remove the task requester from entitlement users list to avoid tainting the results with our own current access to that role, if the requester has it.
        entitlement.members.pop(_user_api_response.get("email"), None)

        # Initialize the Requester object
        requester = models.Requester(
            id=task_summary.get("task_target_user_id"),
            mgmt_chain=_user_api_response.get("mgmtChain"),
            manager=_user_api_response.get("manager"),
            manager_id=_user_api_response.get("manager_id"),
            title=_user_api_response.get("title"),
            department=_user_api_response.get("department"),
            global_job_level=_user_api_response.get("globalJobLevel"),
            supervisory_organization=_user_api_response.get("SupervisoryOrganization"),
            email=_user_api_response.get("email"),
        )

        # Initialize the AccessRequest object
        access_request = models.AccessRequest(
            id=task_summary.get("id"),
            description=task_summary.get("description"),
            duration=task_summary.get("duration"),
            requester=requester,
            entitlement=entitlement,
            # iga_metadata={"policy_step_id": task_summary.get('task_policy_step_id'), "app_entitlement_id": task_summary.get('app_entitlement_id')}
            iga_metadata={"policy_step_id": task_summary.get("task_policy_step_id")},
        )

        return access_request


    def _is_jwt_expired(self, jwt, margin_time=300):
        try:
            # Split the JWT into its three parts
            header, payload, signature = jwt.split(".")

            # Decode the payload
            decoded_payload = self.__base64url_decode(payload)

            # Parse the JSON payload
            payload_data = json.loads(decoded_payload)

            # Get the expiration time (exp claim)
            exp = payload_data.get("exp")

            if exp is None:
                return True

            # Check if the token is expired or within the margin time
            # This means the call to this function will return False
            # if we're within `margin_time` seconds of expiration.
            current_time = int(time.time())
            return current_time > exp - margin_time

        except Exception as e:
            logging.exception("Error checking ConductorOne JWT expiration.")
            return True


    def __base64url_decode(self, input):
        padding = "=" * (4 - len(input) % 4)
        return base64.urlsafe_b64decode(input + padding)
