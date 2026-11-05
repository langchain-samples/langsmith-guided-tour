"""Deployable and managed agent wiring; no network or model calls."""

import ast
import json
import os
from pathlib import Path

os.environ.setdefault("LANGSMITH_GATEWAY_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-key")

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

import agents.client_research_agent as shared
from agents.deployable_agents.client_research import agent as deployable
from utils.config import MANAGED_AGENT_NAME

REPO_ROOT = Path(__file__).resolve().parents[1]
MANAGED_DIR = REPO_ROOT / "agents/managed/client_research"


class ToolCallingFake(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def test_deployment_ships_the_notebook_tools():
    assert deployable.get_client_profile is shared.get_client_profile
    assert deployable.web_search is shared.web_search
    assert not hasattr(deployable, "_CLIENTS")


def test_deployed_agent_continues_after_a_failed_lookup():
    model = ToolCallingFake(messages=iter([
        AIMessage(content="", tool_calls=[{"name": "get_client_profile", "args": {"client_id": "acme-pension"}, "id": "call_1"}]),
        AIMessage(content="I couldn't find that client."),
    ]))
    graph = deployable.build_deployable_agent(model)

    result = graph.invoke({"messages": [{"role": "user", "content": "Pull up Acme Pension Fund."}]})

    tool_messages = [m for m in result["messages"] if m.type == "tool"]
    assert tool_messages[0].status == "error"
    assert result["messages"][-1].content == "I couldn't find that client."


def test_base_research_agent_builds():
    from agents.deployable_agents.base_research_agent import agent as base

    assert base.agent is not None


def test_langgraph_config_uses_the_deploy_env_file():
    config = json.loads((REPO_ROOT / "langgraph.json").read_text())
    assert config["env"] == ".env.deploy"
    assert config["python_version"] == "3.11"
    for target in config["graphs"].values():
        assert (REPO_ROOT / target.split(":")[0]).is_file()
    assert ".env.deploy" in (REPO_ROOT / ".gitignore").read_text().splitlines()


def test_agents_md_has_no_todo_tool():
    for path in (REPO_ROOT / "agents/deployable_agents").glob("*/AGENTS.md"):
        assert "write_todos" not in path.read_text(), path
