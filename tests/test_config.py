from types import SimpleNamespace

import pytest

from utils.config import TracingDestination, default_agent_address, environment_project, tracing_mode


def test_tracing_mode_agent():
    env = {"LANGSMITH_AGENT_ID": "client-research-agent", "LANGSMITH_AGENT_ENVIRONMENT": "development"}
    assert tracing_mode(env) == "agent"


def test_tracing_mode_project_when_only_project_set():
    assert tracing_mode({"LANGSMITH_PROJECT": "langsmith-poc"}) == "project"


def test_tracing_mode_defaults_to_agent():
    assert tracing_mode({}) == "agent"


def test_default_agent_address_fills_missing_vars():
    env = {}
    default_agent_address(env)
    assert env == {"LANGSMITH_AGENT_ID": "client-research-agent", "LANGSMITH_AGENT_ENVIRONMENT": "development"}


def test_default_agent_address_keeps_deployment_value():
    env = {"LANGSMITH_AGENT_ENVIRONMENT": "staging"}
    default_agent_address(env)
    assert env["LANGSMITH_AGENT_ENVIRONMENT"] == "staging"


def test_default_agent_address_skips_project_mode():
    env = {"LANGSMITH_PROJECT": "langsmith-poc"}
    default_agent_address(env)
    assert "LANGSMITH_AGENT_ID" not in env


def test_tracing_mode_conflict():
    env = {"LANGSMITH_AGENT_ID": "client-research-agent", "LANGSMITH_PROJECT": "langsmith-poc"}
    assert tracing_mode(env) == "conflict"


class FakeClient:
    def __init__(self):
        envs = [
            SimpleNamespace(environment=name, tracer_session_id=f"id-{name}", tracer_session_name=f"name-{name}")
            for name in ("LOCAL", "DEVELOPMENT", "STAGING", "PRODUCTION")
        ]
        self.agents = SimpleNamespace(retrieve=lambda agent_id: SimpleNamespace(id=agent_id, environments=envs))

    def read_project(self, *, project_id=None, project_name=None):
        return SimpleNamespace(id=project_id or "id-project", name=project_name, url=f"https://ui/{project_id or project_name}")


def test_environment_project_picks_uppercase_environment(monkeypatch):
    monkeypatch.setattr("utils.config.TRACING_MODE", "agent")
    dest = environment_project(FakeClient(), "local")
    assert dest == TracingDestination("id-LOCAL", "name-LOCAL", "https://ui/id-LOCAL")


def test_environment_project_project_mode(monkeypatch):
    monkeypatch.setattr("utils.config.TRACING_MODE", "project")
    monkeypatch.setattr("utils.config.PROJECT_NAME", "langsmith-poc")
    dest = environment_project(FakeClient())
    assert (dest.project_id, dest.project_name) == ("id-project", "langsmith-poc")


def test_environment_project_conflict_raises(monkeypatch):
    monkeypatch.setattr("utils.config.TRACING_MODE", "conflict")
    with pytest.raises(RuntimeError, match="LANGSMITH_PROJECT"):
        environment_project(FakeClient())
