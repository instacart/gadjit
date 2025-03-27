import pytest
from unittest.mock import MagicMock, patch
from gadjit.plugins.scoring.requester_profile_attribute_proximity.plugin import (
    RequesterProfileAttributeProximityScoringPlugin,
)
from gadjit.models import AccessRequest, Requester, Entitlement

@pytest.fixture
def plugin():
    return RequesterProfileAttributeProximityScoringPlugin({})

@pytest.fixture
def mock_llm_plugin():
    mock = MagicMock()
    mock.query.return_value = '{"overlap_users": [{"user": "user1", "title_and_department": "Software Engineer, Eng"}]}'
    return mock

@pytest.fixture
def access_request():
    requester = Requester(
        id="req_id",
        mgmt_chain=[],
        manager="test_manager",
        manager_id="mgr_id",
        title="Software Engineer",
        department="Engineering",
        global_job_level="L4",
        organizational_unit="Eng - Core Services",
        email="test@example.com"
    )
    entitlement = Entitlement(
        id="ent_id",
        parent_app_id="app_id",
        name="Core Services Access",
        description="Access to core services for engineering team",
        members={
            "user1@example.com": {
                "id": "user1",
                "title_and_department": "Software Engineer, Eng - Core Services",
                "organizational_unit": "Eng - Core Services"
            },
            "user2@example.com": {
                "id": "user2",
                "title_and_department": "Software Engineer, Eng - Core Services",
                "organizational_unit": "Eng - Core Services"
            }
        }
    )
    return AccessRequest(
        id="test_id",
        description="Test request",
        duration=3600,
        requester=requester,
        entitlement=entitlement,
        iga_metadata={}
    )

def test_compute_scores(plugin, mock_llm_plugin, access_request):
    # Test the main scoring functionality
    score = plugin.compute_scores(access_request, mock_llm_plugin)
    assert isinstance(score, float)
    assert 0 <= score <= 1

def test_match_user_properties_to_existing_group_members(plugin, mock_llm_plugin):
    # Test matching user properties
    field_type = "title_and_department"
    field_value = "Software Engineer, Eng"
    entitlement_users = {
        "user1@example.com": {
            "id": "user1",
            "title_and_department": "Software Engineer, Eng - Core Services"
        }
    }
    
    results = plugin._match_user_properties_to_existing_group_members(
        mock_llm_plugin, field_type, field_value, entitlement_users
    )
    assert isinstance(results, list)
    assert len(results) > 0
    assert "user" in results[0]
    assert field_type in results[0]

def test_match_user_properties_to_existing_group_members_empty_users(plugin, mock_llm_plugin):
    # Test with empty entitlement users
    results = plugin._match_user_properties_to_existing_group_members(
        mock_llm_plugin, "title_and_department", "test", {}
    )
    assert results == []

def test_match_user_properties_to_existing_group_members_invalid_type(plugin, mock_llm_plugin):
    # Test with invalid field type
    with pytest.raises(ValueError):
        plugin._match_user_properties_to_existing_group_members(
            mock_llm_plugin, "invalid_type", "test", {"user1@example.com": {"id": "user1"}}
        )

def test_shared_words_percentage(plugin):
    # Test shared words percentage calculation
    str1 = "Software Engineer, Engineering"
    str2 = "Software Engineer, Core Services"
    percentage = plugin._RequesterProfileAttributeProximityScoringPlugin__shared_words_percentage(str1, str2)
    assert isinstance(percentage, float)
    assert 0 <= percentage <= 1
    assert percentage > 0  # Should have some shared words

def test_shared_words_percentage_empty_strings(plugin):
    # Test with empty strings
    percentage = plugin._RequesterProfileAttributeProximityScoringPlugin__shared_words_percentage("", "")
    assert percentage == 0

def test_remove_json_markdown(plugin):
    # Test JSON markdown removal
    input_str = "```json\n{\"test\": \"value\"}\n```"
    result = plugin._RequesterProfileAttributeProximityScoringPlugin__remove_json_markdown(input_str)
    assert result == '{"test": "value"}'

def test_remove_json_markdown_no_markdown(plugin):
    # Test with no markdown
    input_str = '{"test": "value"}'
    result = plugin._RequesterProfileAttributeProximityScoringPlugin__remove_json_markdown(input_str)
    assert result == input_str

def test_match_user_properties_to_entitlement_properties(plugin, mock_llm_plugin):
    # Test matching user properties to entitlement properties
    mock_llm_plugin.query.return_value = '{"relationship_score": 1.2}'
    result = plugin._match_user_properties_to_entitlement_properties(
        mock_llm_plugin,
        "Software Engineer, Engineering",
        "Core Services Access",
        "Access to core services for engineering team"
    )
    assert isinstance(result, float)
    assert 0.5 <= result <= 1.5  # relationship_score should be between 0.5 and 1.5

def test_compute_scores_with_no_matches(plugin, mock_llm_plugin, access_request):
    # Test scoring when no matches are found
    mock_llm_plugin.query.return_value = '{"overlap_users": []}'
    score = plugin.compute_scores(access_request, mock_llm_plugin)
    assert score == 0

def test_compute_scores_with_llm_error(plugin, mock_llm_plugin, access_request):
    # Test handling of LLM errors
    mock_llm_plugin.query.return_value = None
    with pytest.raises(TypeError):
        plugin.compute_scores(access_request, mock_llm_plugin) 