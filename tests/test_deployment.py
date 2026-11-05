"""Unit tests for the deploy helpers; no network."""

import httpx
import pytest
from dotenv import dotenv_values
from langgraph_cli.host_backend import HostBackendClient

from utils.deployment import find_deployment, reply_text, write_env_subset


def test_write_env_subset_copies_only_named_keys(tmp_path):
    source = tmp_path / ".env"
    source.write_text(
        'LANGSMITH_GATEWAY_API_KEY="gw"\nTAVILY_API_KEY="tv"\n'
        'LANGSMITH_AGENT_ENVIRONMENT="development"\nLANGSMITH_API_KEY="ls"\n'
    )
    target = tmp_path / ".env.deploy"
    target.write_text('STALE="x"\n')

    written = write_env_subset(source, target, ["LANGSMITH_GATEWAY_API_KEY", "MISSING", None])

    assert written == ["LANGSMITH_GATEWAY_API_KEY"]
    assert dotenv_values(target) == {"LANGSMITH_GATEWAY_API_KEY": "gw"}


def test_write_env_subset_applies_overrides(tmp_path):
    source = tmp_path / ".env"
    source.write_text('TAVILY_API_KEY="tv"\n')
    target = tmp_path / ".env.deploy"

    written = write_env_subset(source, target, ["TAVILY_API_KEY"], {"LANGSMITH_AGENT_ENVIRONMENT": "staging"})

    assert written == ["TAVILY_API_KEY", "LANGSMITH_AGENT_ENVIRONMENT"]
    assert dotenv_values(target)["LANGSMITH_AGENT_ENVIRONMENT"] == "staging"


def _client(resources, seen):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        return httpx.Response(200, json={"resources": resources})

    return HostBackendClient("https://api.host.langchain.com", "key", transport=httpx.MockTransport(handler))


def test_find_deployment_skips_previews_and_filters_by_agent():
    seen = []
    resources = [
        {"id": "p1", "name": "preview", "is_preview": True, "source_config": {"custom_url": "https://p"}},
        {"id": "d1", "name": "client-research-agent-staging", "source_config": {"custom_url": "https://d"}},
    ]
    deployment = find_deployment(agent_id="client-research-agent", environment="staging", client=_client(resources, seen))

    assert (deployment.id, deployment.api_url) == ("d1", "https://d")
    assert seen[0]["agent_id"] == "client-research-agent"
    assert seen[0]["agent_environment"] == "staging"


def test_find_deployment_matches_name_exactly():
    resources = [
        {"id": "a", "name": "client-research-managed-old", "source_config": {"custom_url": "https://a"}},
        {"id": "b", "name": "client-research-managed", "source_config": {"custom_url": "https://b"}},
    ]
    assert find_deployment(name="client-research-managed", client=_client(resources, [])).id == "b"


@pytest.mark.parametrize(
    "resources",
    [[], [{"id": "d1", "name": "n", "source_config": {}}]],
    ids=["none", "no-url-yet"],
)
def test_find_deployment_raises_lookup_error(resources):
    with pytest.raises(LookupError):
        find_deployment(name="n", client=_client(resources, []))


def test_reply_text_handles_strings_and_blocks():
    assert reply_text({"messages": [{"content": "plain"}]}) == "plain"
    blocks = [{"type": "reasoning", "summary": []}, {"type": "text", "text": "Hello "}, {"type": "text", "text": "there"}]
    assert reply_text({"messages": [{"content": blocks}]}) == "Hello there"
