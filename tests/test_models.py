import pytest
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from gadjit.models import (
    BaseGadjitIGAPlugin,
    BaseGadjitLLMPlugin,
    BaseGadjitScoringPlugin,
    Entitlement,
    Requester,
    AccessRequest
)

def test_base_iga_plugin():
    # Test initialization
    config = {"test": "config"}
    plugin = BaseGadjitIGAPlugin(config)
    assert plugin.config == config
    
    # Test unimplemented methods
    event = {"test": "event"}
    with pytest.raises(NotImplementedError):
        plugin.retrieve_requests(event)
    
    access_request = AccessRequest(
        id="test_id",
        description="test",
        duration=3600,
        requester=Requester(
            id="req_id",
            mgmt_chain=[],
            manager="test_manager",
            manager_id="mgr_id",
            title="test_title",
            department="test_dept",
            global_job_level="test_level",
            organizational_unit="test_ou",
            email="test@example.com"
        ),
        entitlement=Entitlement(
            id="ent_id",
            parent_app_id="app_id",
            name="test_entitlement",
            description="test_desc",
            members=[]
        )
    )
    
    with pytest.raises(NotImplementedError):
        plugin.comment_request(access_request, "test comment")
    
    with pytest.raises(NotImplementedError):
        plugin.approve_request(access_request)
    
    with pytest.raises(NotImplementedError):
        plugin.deny_request(access_request)

def test_base_llm_plugin():
    # Test initialization
    config = {"test": "config"}
    plugin = BaseGadjitLLMPlugin(config)
    assert plugin.config == config
    
    # Test unimplemented method
    with pytest.raises(NotImplementedError):
        plugin.query("system prompt", "user prompt")

def test_base_scoring_plugin():
    # Test initialization
    config = {"test": "config"}
    plugin = BaseGadjitScoringPlugin(config)
    assert plugin.config == config
    
    # Test unimplemented method
    access_request = AccessRequest(
        id="test_id",
        description="test",
        duration=3600,
        requester=Requester(
            id="req_id",
            mgmt_chain=[],
            manager="test_manager",
            manager_id="mgr_id",
            title="test_title",
            department="test_dept",
            global_job_level="test_level",
            organizational_unit="test_ou",
            email="test@example.com"
        ),
        entitlement=Entitlement(
            id="ent_id",
            parent_app_id="app_id",
            name="test_entitlement",
            description="test_desc",
            members=[]
        )
    )
    
    with pytest.raises(NotImplementedError):
        plugin.score(access_request)

def test_entitlement():
    # Test entitlement creation
    entitlement = Entitlement(
        id="test_id",
        parent_app_id="app_id",
        name="test_entitlement",
        description="test_desc",
        members=["user1", "user2"]
    )
    
    assert entitlement.id == "test_id"
    assert entitlement.parent_app_id == "app_id"
    assert entitlement.name == "test_entitlement"
    assert entitlement.description == "test_desc"
    assert entitlement.members == ["user1", "user2"]

def test_requester():
    # Test requester creation
    requester = Requester(
        id="test_id",
        mgmt_chain=["manager1", "manager2"],
        manager="test_manager",
        manager_id="mgr_id",
        title="test_title",
        department="test_dept",
        global_job_level="test_level",
        organizational_unit="test_ou",
        email="test@example.com"
    )
    
    assert requester.id == "test_id"
    assert requester.mgmt_chain == ["manager1", "manager2"]
    assert requester.manager == "test_manager"
    assert requester.manager_id == "mgr_id"
    assert requester.title == "test_title"
    assert requester.department == "test_dept"
    assert requester.global_job_level == "test_level"
    assert requester.organizational_unit == "test_ou"
    assert requester.email == "test@example.com"

def test_access_request():
    # Test access request creation
    requester = Requester(
        id="req_id",
        mgmt_chain=[],
        manager="test_manager",
        manager_id="mgr_id",
        title="test_title",
        department="test_dept",
        global_job_level="test_level",
        organizational_unit="test_ou",
        email="test@example.com"
    )
    
    entitlement = Entitlement(
        id="ent_id",
        parent_app_id="app_id",
        name="test_entitlement",
        description="test_desc",
        members=[]
    )
    
    access_request = AccessRequest(
        id="test_id",
        description="test request",
        duration=3600,
        requester=requester,
        entitlement=entitlement,
        iga_metadata={"test": "metadata"}
    )
    
    assert access_request.id == "test_id"
    assert access_request.description == "test request"
    assert access_request.duration == 3600
    assert access_request.requester == requester
    assert access_request.entitlement == entitlement
    assert access_request.iga_metadata == {"test": "metadata"} 