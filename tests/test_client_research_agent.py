import re

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from agents.client_research_agent import CLIENTS, build_client_research_agent, get_client_profile


class ScriptedModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@tool
def fake_search(query: str) -> str:
    """Search stub."""
    return "no results"


def test_known_id_returns_profile_with_account_number():
    profile = get_client_profile.invoke({"client_id": "CL-0042"})
    assert "Acme Pension Fund" in profile
    assert re.search(r"ACCT-\d{8}", profile)


def test_ids_are_opaque_and_docstring_is_stale():
    assert all(re.fullmatch(r"CL-\d{4}", client_id) for client_id in CLIENTS)
    assert len(CLIENTS) == 5
    assert "'acme-pension'" in get_client_profile.description or "acme-pension" in str(get_client_profile.args)
    assert "CL-" not in get_client_profile.description


def test_miss_message_states_format_only():
    with pytest.raises(ValueError) as exc_info:
        get_client_profile.invoke({"client_id": "acme-pension"})
    message = str(exc_info.value)
    assert "CL-0000" in message
    for client_id, client in CLIENTS.items():
        assert client_id not in message
        assert client["name"] not in message


def test_slug_lookup_returns_error_and_agent_continues():
    script = iter([
        AIMessage(content="", tool_calls=[{"name": "get_client_profile", "args": {"client_id": "acme-pension"}, "id": "call-1"}]),
        AIMessage(content="I couldn't find that client."),
    ])
    agent = build_client_research_agent(model=ScriptedModel(messages=script), search_tool=fake_search)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Profile for Acme Pension Fund?"}]},
        config={"configurable": {"thread_id": "t-1"}},
    )
    errors = [m for m in result["messages"] if isinstance(m, ToolMessage) and m.status == "error"]
    assert len(errors) == 1
    assert errors[0].content.startswith("Error: No client found")
    assert result["messages"][-1].content == "I couldn't find that client."


def test_builder_adds_extra_tools():
    @tool
    def find_client_id(name: str) -> str:
        """Stub."""
        return "CL-0042"

    script = iter([
        AIMessage(content="", tool_calls=[{"name": "find_client_id", "args": {"name": "Acme"}, "id": "call-1"}]),
        AIMessage(content="done"),
    ])
    agent = build_client_research_agent(model=ScriptedModel(messages=script), search_tool=fake_search, extra_tools=[find_client_id])
    result = agent.invoke({"messages": [{"role": "user", "content": "Acme?"}]}, config={"configurable": {"thread_id": "t-2"}})
    found = [m for m in result["messages"] if isinstance(m, ToolMessage) and m.name == "find_client_id"]
    assert found[0].content == "CL-0042"
