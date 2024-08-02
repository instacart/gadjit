import requests
import os
import logging

from json.decoder import JSONDecodeError
from datetime import datetime, timedelta
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import Retry

CLIENT_ID = os.getenv("C1_CLIENT_ID")
CLIENT_SECRET = os.getenv("C1_CLIENT_SECRET")
API_BASE_URL = os.getenv("C1_BASE_URL")


def authenticate():
    # Token endpoint
    """
    Authenticate and retrieve an access token from the API.

    Returns:
        str: The access token for authentication.

    Raises:
        JSONDecodeError: If there is an issue decoding the response content.
        KeyError: If the authentication call does not return an access token.
    """
    token_url = f"{API_BASE_URL}/auth/v1/token"

    # Parameters for token request
    params = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    # Request to get the token
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504, 521],
        allowed_methods=frozenset({"POST"}),
    )
    s = Session()
    s.mount("https://", HTTPAdapter(max_retries=retries))
    response = s.post(token_url, data=params)  # Raise requests.exceptions.RetryError

    try:
        result = response.json()
    except JSONDecodeError as e:
        logging.exception(
            f"The following content caused the JSONDecodeError:\n{response.content}"
        )
        raise e

    try:
        access_token = result["access_token"]
    except KeyError as e:
        logging.exception(
            f"The ConducutorOne authentication call did not return an access token. Response:\n{response.content}"
        )
        raise e

    return access_token


def search_tasks(access_token):
    """
    Search for tasks using the provided access token.

    Args:
        access_token (str): The access token used for authentication.

    Returns:
        list: A list of dictionaries containing task summaries.

    Raises:
        HTTPError: If the HTTP request returns an unsuccessful status code.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{API_BASE_URL}/api/v1/search/tasks"

    # Prepare time-related search operators
    now = datetime.utcnow()
    one_minute_ago = now - timedelta(
        seconds=65
    )  # cron runs once per minute, adding a few seconds of grace
    created_after = one_minute_ago.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Prepare the payload
    payload = {
        "taskStates": ["TASK_STATE_OPEN"],
        "createdAfter": created_after,
        "currentStep": "TASK_SEARCH_CURRENT_STEP_APPROVAL",  # Only tasks awaiting an approval
    }

    # Send the POST request
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    task_summaries = []

    # Walk the responses and get the attributes we're going to want to use later
    # NOTE: THIS DOES NOT CURRENTLY SUPPORT PAGINATION so re-use carefully. Since
    # we never expect to have more than 1-2 new access requests in the last 60 seconds, a lack
    # of pagination isn't going to be a problem.
    for task in response.json().get("list"):
        task_id = task.get("task", {}).get("id")
        task_description = task.get("task", {}).get("description")
        task_duration = task.get("task", {}).get("duration")
        task_policy_step_id = (
            task.get("task", {}).get("policy", {}).get("current", {}).get("id")
        )
        app_id = task.get("task", {}).get("type", {}).get("grant", {}).get("appId")
        app_entitlement_id = (
            task.get("task", {})
            .get("type", {})
            .get("grant", {})
            .get("appEntitlementId")
        )
        task_target_user_id = task.get("task", {}).get("userId")

        task_summary = {
            "id": task_id,
            "task_target_user_id": task_target_user_id,
            "app_id": app_id,
            "app_entitlement_id": app_entitlement_id,
            "description": task_description,
            "duration": task_duration,
            "task_policy_step_id": task_policy_step_id,
        }
        task_summaries.append(task_summary)

    return task_summaries


def get_user(access_token, user_id):
    # Prepare header with the access token
    """
    Get user details based on the access token and user ID.

    Args:
        access_token (str): Access token for authorization.
        user_id (str): User ID for fetching user details.

    Returns:
        dict: User profile data including manager information.

    Raises:
        requests.HTTPError: If there is an HTTP error response from the API.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{API_BASE_URL}/api/v1/users/{user_id}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_data = response.json()

    managers = response_data.get("userView", {}).get("user", {}).get("managerIds", [])
    if len(managers) > 0:
        manager_id = (
            response_data.get("userView", {}).get("user", {}).get("managerIds")[0]
        )
    else:
        manager_id = None
        _logged_user_object = response_data.get("userView", {})
        logging.warning(f"No manager was found on this user: {_logged_user_object}")

    profile = response_data.get("userView", {}).get("user", {}).get("profile", {})
    profile["manager_id"] = manager_id

    return profile


def get_entitlement(access_token, app_id, app_entitlement_id):
    """
    Get the entitlement data for a specific app and entitlement ID.

    Args:
        access_token (str): The access token used for authentication.
        app_id (str): The ID of the app.
        app_entitlement_id (str): The ID of the entitlement.

    Returns:
        dict: The entitlement data for the specified app and entitlement ID.

    Raises:
        HTTPError: If the GET request to the API endpoint fails.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{API_BASE_URL}/api/v1/apps/{app_id}/entitlements/{app_entitlement_id}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_data = response.json()
    return response_data


def get_entitlement_members(access_token, app_id, app_entitlement_id):
    """
    Get the members of an entitlement from an app.

    Args:
        access_token (str): The access token for authentication.
        app_id (str): The ID of the app.
        app_entitlement_id (str): The ID of the app entitlement.

    Returns:
        dict: A dictionary containing the entitlement users with their details.

    Raises:
        HTTPError: If the response status code is not successful.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{API_BASE_URL}/api/v1/apps/{app_id}/entitlements/{app_entitlement_id}/users"

    # Initialize pageToken to None for the first request
    page_token = None
    search_params = {}
    entitlement_users = {}

    # Loop until there are no more pages to request
    while True:
        # If pageToken exists, add it to the search parameters
        if page_token:
            search_params["page_token"] = page_token

        # Make the search request
        response = requests.get(url, headers=headers, params=search_params)
        response.raise_for_status()
        response_data = response.json()
        page_token = response_data.get("nextPageToken")

        # Extract entitlements from response
        users = response_data["list"]
        for user in users:
            okta_user = user.get("appUser").get("appUser")
            email = okta_user.get("email")
            profile = okta_user.get("profile")

            entitlement_users[email] = {
                "id": okta_user.get("identityUserId"),
                "manager": profile.get("manager"),
                "mgmtChain": profile.get("mgmtChain"),
                "title": profile.get("title"),
                "department": profile.get("department"),
                "title_and_department": f"{profile.get('title')}, {profile.get('department')}",
                "SupervisoryOrganization": profile.get("SupervisoryOrganization"),
                "globalJobLevel": profile.get("globalJobLevel"),
            }

        # Check if there's another page
        if not page_token:
            break  # Exit loop if no nextPageToken is present

    return entitlement_users


def comment_task(access_token, task_id, comment):
    """
    Add a comment to a task using the provided access token.

    Args:
        access_token (str): The access token for authentication.
        task_id (int): The ID of the task to add the comment to.
        comment (str): The comment to be added to the task.

    Raises:
        HTTPError: If the POST request to add a comment fails.

    Returns:
        None
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{API_BASE_URL}/api/v1/tasks/{task_id}/action/comment"

    payload = {"comment": comment}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()


def reassign_task(access_token, task_id, task_policy_step_id, reassign_to_user):
    """
    Reassign a task to a different user.

    Args:
        access_token (str): The access token for authentication.
        task_id (int): The ID of the task to be reassigned.
        task_policy_step_id (int): The ID of the policy step related to the task.
        reassign_to_user (int): The ID of the user to reassign the task to.

    Raises:
        HTTPError: If the POST request to reassign the task fails.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{API_BASE_URL}/api/v1/tasks/{task_id}/action/reassign"

    payload = {
        "policyStepId": task_policy_step_id,
        "newStepUserIds": [reassign_to_user],
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()


def get_task(access_token, task_id):
    """
    Retrieve information about a specific task from the API.

    Args:
        access_token (str): The access token for authentication.
        task_id (int): The ID of the task to retrieve.

    Returns:
        dict: A dictionary containing information about the task.

    Raises:
        None.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{API_BASE_URL}/api/v1/tasks/{task_id}"

    response = requests.get(url, headers=headers)
    response_data = response.json()
    return response_data


def approve_task(access_token, task_id, task_policy_step_id):
    """
    Approve a task with the specified task ID and policy step ID using the provided access token.

    Args:
        access_token (str): The access token for authentication.
        task_id (str): The ID of the task to approve.
        task_policy_step_id (str): The ID of the policy step for the task.

    Raises:
        HTTPError: If the HTTP request to approve the task fails.

    Returns:
        dict: The JSON response data after approving the task.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{API_BASE_URL}/api/v1/tasks/{task_id}/action/approve"

    # Prepare the payload
    payload = {
        "policyStepId": task_policy_step_id,
        "comment": "Manager approval is no longer required and your access has been granted. Have a wonderful day!",
    }

    # Send the POST request
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_data = response.json()
