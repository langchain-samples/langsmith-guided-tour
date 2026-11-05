"""Names shared by every module: the agent, its environments, datasets and the tracing destination."""

import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=True)

AGENT_NAME = os.getenv("LANGSMITH_AGENT_ID", "client-research-agent")
AGENT_ENVIRONMENT = os.getenv("LANGSMITH_AGENT_ENVIRONMENT", "development")
BUILD_ENVIRONMENT = "local"
DEPLOY_ENVIRONMENT = "staging"
PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "langsmith-poc")
GOLDEN_DATASET = "client-research-golden"
ENGINE_EXAMPLES_DATASET = "client-research-engine-examples"
REVIEW_QUEUE = "client-research-review"
MANAGED_AGENT_NAME = "client-research-managed"
# Not LANGSMITH_GATEWAY_API_KEY: LangSmith treats that secret name as "bill this workspace".
WORKSPACE_GATEWAY_SECRET = "GATEWAY_MODEL_API_KEY"
WORKSPACE_MODEL_CONFIG = "client-research-model"

# Which agent the notebooks build, trace and evaluate. To add one, expose a
# build_<name>() factory under agents/ and add a branch in load_active_agent().
ACTIVE_AGENT = "client_research_agent"

TracingMode = Literal["agent", "project", "conflict"]


def tracing_mode(env: Mapping[str, str]) -> TracingMode:
    """Name the tracing destination the given environment variables select."""
    has_agent = bool(env.get("LANGSMITH_AGENT_ID") or env.get("LANGSMITH_AGENT_ENVIRONMENT"))
    has_project = bool(env.get("LANGSMITH_PROJECT"))
    if has_agent and has_project:
        return "conflict"
    if has_project:
        return "project"
    return "agent"


def default_agent_address(env: MutableMapping[str, str]) -> None:
    """Point tracing at the tour's agent unless a project is configured."""
    if env.get("LANGSMITH_PROJECT"):
        return
    # The SDK reads only os.environ and caches it; setdefault lets a deployment's own value win.
    env.setdefault("LANGSMITH_AGENT_ID", AGENT_NAME)
    env.setdefault("LANGSMITH_AGENT_ENVIRONMENT", AGENT_ENVIRONMENT)


default_agent_address(os.environ)
TRACING_MODE = tracing_mode(os.environ)


@dataclass(frozen=True)
class TracingDestination:
    project_id: str
    project_name: str
    url: str


def environment_project(client, environment: str = AGENT_ENVIRONMENT) -> TracingDestination:
    """Return the tracing project behind an agent environment, or the fallback project."""
    if TRACING_MODE == "conflict":
        raise RuntimeError("Set the LANGSMITH_AGENT_* variables or LANGSMITH_PROJECT in .env, not both.")

    if TRACING_MODE == "project":
        project = client.read_project(project_name=PROJECT_NAME)
        return TracingDestination(str(project.id), project.name, project.url)

    agent = client.agents.retrieve(AGENT_NAME)
    # The SDK's environment enum is uppercase.
    matches = [env for env in agent.environments if env.environment == environment.upper()]
    if not matches:
        raise RuntimeError(f"Agent {AGENT_NAME} has no {environment} environment.")
    env = matches[0]
    project = client.read_project(project_id=env.tracer_session_id)
    return TracingDestination(env.tracer_session_id, env.tracer_session_name, project.url)


def load_active_agent():
    """Return a freshly built instance of the active agent."""
    if ACTIVE_AGENT == "client_research_agent":
        from agents.client_research_agent import build_client_research_agent

        return build_client_research_agent()
    if ACTIVE_AGENT == "base_research_agent":
        from agents.deployable_agents.base_research_agent.agent import agent

        return agent
    raise ValueError(f"Unknown ACTIVE_AGENT: {ACTIVE_AGENT!r}")
