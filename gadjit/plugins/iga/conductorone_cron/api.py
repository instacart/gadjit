import requests
import logging

from json.decoder import JSONDecodeError
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import Retry


class ConductorOneAPIClient:
    """
    A class representing an API client for ConductorOne.

    Attributes:
        config (dict): A dictionary containing configuration values.
    """

    def __init__(self, config):
        """
        Initialize the class with a configuration object.

        Args:
            config (object): The configuration object to be stored.

        Returns:
            None
        """
        self.config = config

    def authenticate(self):

        # Token endpoint
        """
        Authenticate the user with ConducutorOne API.

        Raises a JSONDecodeError if the response content cannot be decoded as JSON, or a KeyError if the authentication call does not return an access token.

        Returns:
            str: The access token for authentication.
        """
        token_url = f"{self.config.get('base_url')}/auth/v1/token"

        # Parameters for token request
        params = {
            "grant_type": "client_credentials",
            "client_id": self.config.get("client_id"),
            "client_secret": self.config.get("client_secret"),
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
        response = s.post(
            token_url, data=params
        )  # Raise requests.exceptions.RetryError

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

    def search_tasks(self, access_token, created_after):
        """
        Search for tasks based on criteria and retrieve task summaries.

        Args:
            access_token (str): The access token used for authentication.
            created_after (str): The timestamp after which tasks were created.

        Returns:
            list: A list of dictionaries containing task summaries.

        Raises:
            HTTPError: If the HTTP request to the API fails.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self.config.get('base_url')}/api/v1/search/tasks"

        payload = {
            "taskStates": ["TASK_STATE_OPEN"],
            "createdAfter": created_after,
            "currentStep": "TASK_SEARCH_CURRENT_STEP_APPROVAL",  # Only tasks awaiting an approval
            "taskTypes": [
                {
                    "grant": {}
                }
            ],
        }

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

    def get_user(self, access_token, user_id):
        """
        Get user profile details by user ID using the provided access token.

        Args:
            access_token (str): Access token for authentication.
            user_id (str): ID of the user whose profile details need to be fetched.

        Returns:
            dict: User profile details including manager ID.

        Raises:
            requests.exceptions.HTTPError: If a HTTP error response is received.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.config.get('base_url')}/api/v1/users/{user_id}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_data = response.json()

        managers = (
            response_data.get("userView", {}).get("user", {}).get("managerIds", [])
        )
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

    def get_entitlement(self, access_token, app_id, app_entitlement_id):
        """
        Get the entitlement details for a given app and entitlement ID.

        Args:
            access_token (str): The access token for authentication.
            app_id (str): The ID of the app.
            app_entitlement_id (str): The ID of the app entitlement.

        Returns:
            dict: JSON response containing the entitlement details.

        Raises:
            HTTPError: If the HTTP request returns an error status code.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self.config.get('base_url')}/api/v1/apps/{app_id}/entitlements/{app_entitlement_id}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        return response_data

    def get_entitlement_members(self, access_token, app_id, app_entitlement_id):
        """
        Get the list of entitlement members for a specific app entitlement.

        Args:
            self: The object instance.
            access_token (str): The access token for authentication.
            app_id (str): The ID of the application.
            app_entitlement_id (str): The ID of the app entitlement.

        Returns:
            dict: A dictionary containing the entitlement users' details.

        Raises:
            HTTPError: If there is an HTTP error response from the API.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self.config.get('base_url')}/api/v1/apps/{app_id}/entitlements/{app_entitlement_id}/users"

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
                    "organizational_unit": profile.get("SupervisoryOrganization"),
                    "globalJobLevel": profile.get("globalJobLevel"),
                }

            # Check if there's another page
            if not page_token:
                break  # Exit loop if no nextPageToken is present

        return entitlement_users

    def comment_task(self, access_token, task_id, comment):
        """
        Add a comment to a task using the specified access token.

        Args:
            access_token (str): The access token for authentication.
            task_id (str): The ID of the task to add the comment to.
            comment (str): The content of the comment to be added.

        Raises:
            requests.exceptions.HTTPError: If the POST request to add the comment fails.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self.config.get('base_url')}/api/v1/tasks/{task_id}/action/comment"

        payload = {"comment": comment}

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

    def reassign_task(
        self, access_token, task_id, task_policy_step_id, reassign_to_user
    ):
        """
        Reassign a task to a different user.

        Args:
            access_token (str): The access token for authentication.
            task_id (str): The unique identifier of the task.
            task_policy_step_id (str): The policy step ID of the task.
            reassign_to_user (str): The user ID to reassign the task to.

        Raises:
            HTTPError: If the request to reassign the task fails.

        Returns:
            None
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self.config.get('base_url')}/api/v1/tasks/{task_id}/action/reassign"

        payload = {
            "policyStepId": task_policy_step_id,
            "newStepUserIds": [reassign_to_user],
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

    def get_task(self, access_token, task_id):
        """
        Get a specific task using the provided access token and task ID.

        Args:
            access_token (str): A valid access token for authentication.
            task_id (str): The ID of the task to retrieve.

        Returns:
            dict: The data of the requested task.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.config.get('base_url')}/api/v1/tasks/{task_id}"

        response = requests.get(url, headers=headers)
        response_data = response.json()
        return response_data

    def approve_task(self, access_token, task_id, task_policy_step_id):
        """
        Approve a task by sending a request to the API.

        Args:
            access_token (str): The access token for authentication.
            task_id (int): The ID of the task to approve.
            task_policy_step_id (int): The ID of the task policy step.

        Returns:
            None

        Raises:
            requests.HTTPError: If the request to the API fails.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.config.get('base_url')}/api/v1/tasks/{task_id}/action/approve"

        # Prepare the payload
        payload = {
            "policyStepId": task_policy_step_id,
            "comment": "Manual approval is no longer required and your access has been granted. Have a wonderful day!",
        }

        # Send the POST request
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()

    def deny_task(self, access_token, task_id, task_policy_step_id):
        """
        Deny a task by sending a request to the API.

        Args:
            access_token (str): The access token for authentication.
            task_id (int): The ID of the task to deny.
            task_policy_step_id (int): The ID of the task policy step.

        Returns:
            None

        Raises:
            requests.HTTPError: If the request to the API fails.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.config.get('base_url')}/api/v1/tasks/{task_id}/action/deny"

        # Prepare the payload
        payload = {
            "policyStepId": task_policy_step_id,
            "comment": "This request has been closed.",
        }

        # Send the POST request
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
