class BaseGadjitIGAPlugin:
    def __init__(self, config):
        self.config = config

    def retrieve_requests(self, event):
        raise NotImplementedError("Plugin must implement the retrieve_requests method.")


class BaseGadjitLLMPlugin:
    def __init__(self, config):
        self.config = config

    def query(self, system_prompt, user_prompt):
        raise NotImplementedError("Plugin must implement the query method.")


class BaseGadjitScoringPlugin:
    def __init__(self, config):
        self.config = config

    def score(self, access_request):
        raise NotImplementedError("Plugin must implement the score method.")


class Entitlement:
    def __init__(self, id, parent_app_id, name, description, members):
        self.id = id
        self.parent_app_id = parent_app_id
        self.name = name
        self.description = description
        self.members = members


class Requester:
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
    def __init__(
        self, id, description, duration, requester, entitlement, iga_metadata={}
    ):
        self.id = id
        self.description = description
        self.duration = duration
        self.requester = requester
        self.entitlement = entitlement
        self.iga_metadata = iga_metadata
