class Entitlement:
    """
    A class representing an entitlement.

    Attributes:
        id (int): The unique identifier for the entitlement.
        parent_app_id (int): The parent application's identifier.
        name (str): The name of the entitlement.
        description (str): A description of the entitlement.
        members (list): A list of members associated with the entitlement.
    """

    def __init__(self, id, parent_app_id, name, description, members):
        """
        Initialize a new instance of a custom class with the provided attributes.

        Args:
            id (int): The unique identifier for the instance.
            parent_app_id (int): The identifier of the parent application.
            name (str): The name of the instance.
            description (str): A brief description of the instance.
            members (list): A list of members associated with the instance.

        Returns:
            None

        Raises:
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
        mgmt_chain (list): A list representing the management chain of the requester.
        manager (str): The name of the requester's manager.
        manager_id (int): The unique identifier for the requester's manager.
        title (str): The job title of the requester.
        department (str): The department the requester is in.
        title_and_department (str): A formatted string containing both the job title and department of the requester.
        global_job_level (int): The global job level of the requester.
        supervisory_organization (str): The supervisory organization of the requester.
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
        Initialize a new employee object with the given attributes.

        Args:
            id (int): The unique identifier for the employee.
            mgmt_chain (list): The management chain of the employee.
            manager (str): The name of the employee's manager.
            manager_id (int): The unique identifier of the employee's manager.
            title (str): The job title of the employee.
            department (str): The department the employee belongs to.
            global_job_level (int): The global job level of the employee.
            supervisory_organization (str): The supervisory organization of the employee.
            email (str): The email address of the employee.

        Attributes:
            id (int): The unique identifier for the employee.
            mgmt_chain (list): The management chain of the employee.
            manager (str): The name of the employee's manager.
            manager_id (int): The unique identifier of the employee's manager.
            title (str): The job title of the employee.
            department (str): The department the employee belongs to.
            title_and_department (str): The combination of title and department.
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
        id (int): The unique identifier for the access request.
        description (str): A description of the access request.
        duration (int): The duration of the access request in days.
        requester (str): The name of the requester of the access.
        entitlement (str): The entitlement being requested.
        iga_metadata (dict): Additional metadata related to the access request, default is an empty dictionary.
    """

    def __init__(
        self, id, description, duration, requester, entitlement, iga_metadata={}
    ):
        """
        Initialize a new instance of a class.

        Args:
            id (int): The unique identifier for the instance.
            description (str): A description of the instance.
            duration (int): The duration of the instance.
            requester (str): The requester of the instance.
            entitlement (str): The entitlement of the instance.
            iga_metadata (dict, optional): Additional metadata for the instance. Defaults to an empty dictionary.

        Returns:
            None
        """
        self.id = id
        self.description = description
        self.duration = duration
        self.requester = requester
        self.entitlement = entitlement
        self.iga_metadata = iga_metadata
