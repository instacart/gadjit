class BaseGadjitIGAPlugin:
    """
    Base class for Gadjit IGA plugins.

    Attributes:
        config (dict): The configuration settings for the plugin.
    """

    def __init__(self, config):
        """
        Initialize the object with a configuration.

        Args:
            config: The configuration to be stored in the object.

        Returns:
            None
        """
        self.config = config

    def retrieve_requests(self, event):
        """
        Retrieve a list of requests, either by pull or push based on the event provided.

        This method should be implemented by the plugin to retrieve requests based on the event.

        Args:
            event: The event triggering the request retrieval.

        Raises:
            NotImplementedError: If the method is called without being implemented by the plugin.
        """
        raise NotImplementedError("Plugin must implement the retrieve_requests method.")

    def comment_request(self, access_request, comment):
        """
        Comment on an open access request.

        Args:
            access_request (AccessRequest): The access request object.
            comment (str): The comment to be added to the access request.

        Returns:
            None

        Raises:
            NotImplementedError: If the method is called without being implemented by the plugin.
        """
        raise NotImplementedError("Plugin must implement the comment_request method.")

    def approve_request(self, access_request):
        """
        Approve a user access request.

        Args:
            access_request (AccessRequest): An object representing the access request to be approved.

        Returns:
            None

        Raises:
            NotImplementedError: If the method is called without being implemented by the plugin.
        """
        raise NotImplementedError("Plugin must implement the approve_request method.")

    def deny_request(self, access_request):
        """
        Deny a specific access request.

        Args:
            access_request (object): The access request object to be denied.

        Returns:
            None

        Raises:
            NotImplementedError: If the method is called without being implemented by the plugin.
        """
        raise NotImplementedError("Plugin must implement the deny_request method.")


class BaseGadjitLLMPlugin:
    """
    Base class for Gadjit LLM plugins.

    Attributes:
        config: The configuration settings for the plugin.
    """

    def __init__(self, config):
        """
        Initialize the object with a configuration dictionary.

        Args:
            config (dict): A dictionary containing configuration settings.

        Returns:
            None
        """
        self.config = config

    def query(self, system_prompt, user_prompt):
        """
        Query the user using system and user prompts.

        This method must be implemented by the plugin.

        Args:
            system_prompt (str): The prompt displayed to the system.
            user_prompt (str): The prompt displayed to the user.

        Raises:
            NotImplementedError: If the method is not implemented by the plugin.
        """
        raise NotImplementedError("Plugin must implement the query method.")


class BaseGadjitScoringPlugin:
    """
    Base class for scoring plugins for Gadjit.

    Attributes:
        config (dict): Configuration options for the plugin.
    """

    def __init__(self, config):
        """
        Initialize the object with the provided configuration.

        Args:
            config (dict): A dictionary containing configuration settings.

        Returns:
            None
        """
        self.config = config

    def score(self, access_request):
        """
        Calculate the score of an access request.

        Args:
            access_request (object): An access request object.

        Raises:
            NotImplementedError: If the plugin does not implement the score method.
        """
        raise NotImplementedError("Plugin must implement the score method.")


class Entitlement:
    """
    A class representing an entitlement.

    Attributes:
        id (int): The unique identifier for the entitlement.
        parent_app_id (int): The unique identifier for the parent app.
        name (str): The name of the entitlement.
        description (str): The description of the entitlement.
        members (list): A list of members associated with the entitlement.
    """

    def __init__(self, id, parent_app_id, name, description, members):
        """
        Initialize a new instance of a class.

        Args:
            id (int): The ID of the instance.
            parent_app_id (int): The parent application ID.
            name (str): The name of the instance.
            description (str): The description of the instance.
            members (list): A list of members associated with the instance.

        Returns:
            None
        """
        self.id = id
        self.parent_app_id = parent_app_id
        self.name = name
        self.description = description
        self.members = members


class Requester:
    """
    A class representing a requester.

    Attributes:
        id (int): The unique identifier for the requester.
        mgmt_chain (str): The management chain the requester belongs to.
        manager (str): The requester's manager.
        manager_id (int): The unique identifier for the requester's manager.
        title (str): The requester's job title.
        department (str): The department the requester belongs to.
        title_and_department (str): The formatted string combining the title and department.
        global_job_level (int): The global job level of the requester.
        supervisory_organization (str): The supervisory organization the requester belongs to.
        email (str): The email address of the requester.
    """

    def __init__(
        self,
        id,
        mgmt_chain,
        manager,
        manager_id,
        title,
        department,
        global_job_level,
        supervisory_organization,
        email,
    ):
        """
        Initialize an Employee object with the given attributes.

        Args:
            id (int): The employee ID.
            mgmt_chain (str): The management chain of the employee.
            manager (str): The name of the employee's manager.
            manager_id (int): The ID of the employee's manager.
            title (str): The job title of the employee.
            department (str): The department the employee works in.
            global_job_level (int): The global job level of the employee.
            supervisory_organization (str): The supervisory organization of the employee.
            email (str): The email address of the employee.
        """
        self.id = id
        self.mgmt_chain = mgmt_chain
        self.manager = manager
        self.manager_id = manager_id
        self.title = title
        self.department = department
        self.title_and_department = f"{title}, {department}"
        self.global_job_level = global_job_level
        self.supervisory_organization = supervisory_organization
        self.email = email


class AccessRequest:
    """
    A class representing an access request.

    Attributes:
        id (int): The unique identifier for the request.
        description (str): The description of the request.
        duration (int): The duration for which the access is requested.
        requester (str): The name of the requester.
        entitlement (str): The entitlement being requested.
        iga_metadata (dict): Additional metadata related to the request. Default is an empty dictionary.
    """

    def __init__(
        self, id, description, duration, requester, entitlement, iga_metadata={}
    ):
        """
        Initialize a new object with the given parameters.

        Args:
            id (int): The unique identifier for the object.
            description (str): A description of the object.
            duration (int): The duration of the object.
            requester (str): The requester of the object.
            entitlement (str): The entitlement of the object.
            iga_metadata (dict, optional): Additional metadata for the object. Defaults to an empty dictionary.

        Returns:
            None.
        """
        self.id = id
        self.description = description
        self.duration = duration
        self.requester = requester
        self.entitlement = entitlement
        self.iga_metadata = iga_metadata
