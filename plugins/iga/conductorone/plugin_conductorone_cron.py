import base64
import json
import time
import models
from . import api

ACCESS_TOKEN = None
REASSIGN_TO_USER = os.getenv('C1_REASSIGN_TO_USER')

def initialize():
    pass


def get_access_requests(event):
    access_requests = []
    task_summaries = api.search_tasks(_get_access_token())
    for task_summary in task_summaries:
        access_request = _prepare_context_objects(_get_access_token(), task_summary)
        access_requests.append(access_request)

    return access_requests


def comment_request(access_request, comment):
    api.comment_task(_get_access_token(), access_request.id, comment)


def approve_request(access_request):
    # Assign this task to the C1 admin account which this bot runs as.
    api.reassign_task(_get_access_token(), access_request.id, access_request.iga_metadata.get('policy_step_id'), REASSIGN_TO_USER)

    # Reassignment causes us to move to another step, which we need to get the ID of.
    new_task_policy_step_id = api.get_task(_get_access_token(), access_request.id).get('taskView').get('task', {}).get('policy', {}).get('current', {}).get('id')

    # Send the approval.
    api.approve_task(_get_access_token(), access_request.id, new_task_policy_step_id)


def deny_request(access_request):
    pass


def _get_access_token():
    global ACCESS_TOKEN

    if not ACCESS_TOKEN or _is_jwt_expired(ACCESS_TOKEN):
        ACCESS_TOKEN = api.authenticate()

    return ACCESS_TOKEN


def _prepare_context_objects(access_token, task_summary):
    # Get information about the entitlement this task is requesting
    _entitlement_api_response = api.get_entitlement(access_token, task_summary.get('app_id'), task_summary.get('app_entitlement_id'))
    _entitlement_members_api_response = api.get_entitlement_members(access_token, task_summary.get('app_id'), task_summary.get('app_entitlement_id'))

    # Initialize the Entitlement object
    entitlement = models.Entitlement(
        id=task_summary.get('app_entitlement_id'),
        parent_app_id=task_summary.get('app_id'),
        name=_entitlement_api_response.get('appEntitlementView', {}).get('appEntitlement', {}).get('displayName').replace(" Group Member", ""),
        description=_entitlement_api_response.get('appEntitlementView', {}).get('appEntitlement', {}).get('description'),
        members=_entitlement_members_api_response
    )

    # Get information about the user who requested this task
    _user_api_response = api.get_user(access_token, task_summary.get('task_target_user_id'))

    # Remove the task requester from entitlement users list to avoid tainting the results with our own current access to that role, if the requester has it.
    entitlement.members.pop(_user_api_response.get('email'), None)

    # Initialize the Requester object
    requester = models.Requester(
        id=task_summary.get('task_target_user_id'),
        mgmt_chain=_user_api_response.get('mgmtChain'),
        manager=_user_api_response.get('manager'),
        manager_id=_user_api_response.get('manager_id'),
        title=_user_api_response.get('title'),
        department=_user_api_response.get('department'),
        global_job_level=_user_api_response.get('globalJobLevel'),
        supervisory_organization=_user_api_response.get('SupervisoryOrganization'),
        email=_user_api_response.get('email')
    )

    # Initialize the AccessRequest object
    access_request = models.AccessRequest(
       id=task_summary.get('id'),
       description=task_summary.get('description'),
       duration=task_summary.get('duration'),
       requester=requester,
       entitlement=entitlement,
       #iga_metadata={"policy_step_id": task_summary.get('task_policy_step_id'), "app_entitlement_id": task_summary.get('app_entitlement_id')}
       iga_metadata={"policy_step_id": task_summary.get('task_policy_step_id')}
    )

    return access_request


def _is_jwt_expired(jwt, margin_time=300):
    try:
        # Split the JWT into its three parts
        header, payload, signature = jwt.split('.')
        
        # Decode the payload
        decoded_payload = __base64url_decode(payload)
        
        # Parse the JSON payload
        payload_data = json.loads(decoded_payload)
        
        # Get the expiration time (exp claim)
        exp = payload_data.get('exp')
        
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


def __base64url_decode(input):
    padding = '=' * (4 - len(input) % 4)
    return base64.urlsafe_b64decode(input + padding)

