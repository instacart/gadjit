"""Request-contract tests; never contact OpenAI, AWS, or ConductorOne."""

import json
from unittest.mock import Mock

import pytest
from botocore.credentials import Credentials

from gadjit.plugins.llm.aws_api_gateway_openai_proxy.plugin import (
    AWSAPIGatewayOpenAIProxyPlugin,
)
from gadjit.plugins.llm.openai.plugin import OpenAIPlugin


@pytest.fixture(params=["direct", "proxy"])
def llm_transport(request, monkeypatch):
    response = Mock()
    send = Mock(return_value=response)

    if request.param == "direct":
        plugin = OpenAIPlugin({"secret_key": "test-key"})
        monkeypatch.setattr(
            "gadjit.plugins.llm.openai.plugin.requests.post", send
        )
    else:
        plugin = AWSAPIGatewayOpenAIProxyPlugin(
            {"api_gateway_url": "https://example.invalid/proxy/openai/v1/chat/completions"}
        )
        # Exercise the real SigV4 serialization/signing path without STS or AWS credentials.
        monkeypatch.setattr(
            plugin,
            "_get_access_token",
            Mock(return_value=Credentials("test-access-key", "test-secret-key")),
        )
        monkeypatch.setattr(
            "gadjit.plugins.llm.aws_api_gateway_openai_proxy.plugin.requests.request",
            send,
        )

    return request.param, plugin, send, response


def test_luna_request_and_response(llm_transport):
    transport, plugin, send, response = llm_transport
    response.json.return_value = {
        "model": "gpt-6-luna",
        "choices": [
            {"finish_reason": "stop", "message": {"content": "Review explanation"}}
        ],
    }

    assert plugin.query("Review access safely", "A synthetic user's request") == (
        "Review explanation"
    )
    send.assert_called_once()
    kwargs = send.call_args.kwargs
    if transport == "direct":
        payload = kwargs["json"]
        assert send.call_args.args == (
            "https://api.openai.com/v1/chat/completions",
        )
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    else:
        payload = json.loads(kwargs["data"])
        assert kwargs["method"] == "POST"
        assert kwargs["url"] == (
            "https://example.invalid/proxy/openai/v1/chat/completions"
        )
        assert kwargs["headers"]["Authorization"].startswith("AWS4-HMAC-SHA256 ")

    # Exact contract excludes obsolete max_tokens and sampling/penalty parameters.
    assert payload == {
        "model": "gpt-6-luna",
        "messages": [
            {"role": "system", "content": "Review access safely"},
            {"role": "user", "content": "A synthetic user's request"},
        ],
        "reasoning_effort": "none",
        "max_completion_tokens": 512,
    }


@pytest.mark.parametrize("finish_reason", ["length", "content_filter", "tool_calls"])
def test_incomplete_response_is_not_used(llm_transport, finish_reason):
    _, plugin, _, response = llm_transport
    response.json.return_value = {
        "choices": [
            {"finish_reason": finish_reason, "message": {"content": "Partial reply"}}
        ]
    }

    assert plugin.query("System prompt", "User prompt") is None


def test_api_error_is_propagated(llm_transport):
    _, plugin, _, response = llm_transport
    response.json.return_value = {"error": {"message": "Model is unavailable"}}

    with pytest.raises(Exception, match="Model is unavailable"):
        plugin.query("System prompt", "User prompt")
