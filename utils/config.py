"""Tour-wide configuration: which agent to run against and which LangSmith project.

Edit ACTIVE_AGENT to swap workloads. Deployed engineers adding a new use case
should register their agent here, not edit individual notebooks.
"""

import os

# Which agent the tour notebooks build/trace/evaluate against.
#   "research_agent" — the fully-implemented research deep agent (NB02-06 default)
#   "deep_agent"     — the stock writer agent (referenced by NB06 / deploy)
# To add a new agent: expose a build_<name>() factory under agents/,
# add a branch below, and update ACTIVE_AGENT here.
ACTIVE_AGENT = "research_agent"

# LangSmith project name used across notebooks. Override per-environment via
# the LANGSMITH_PROJECT env var.
PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "langsmith-poc-tour")


def load_active_agent():
    """Return a freshly built instance of the active agent."""
    if ACTIVE_AGENT == "research_agent":
        from agents.research_agent import build_research_agent
        return build_research_agent()
    if ACTIVE_AGENT == "deep_agent":
        from agents.deep_agent.agent import agent
        return agent
    raise ValueError(f"Unknown ACTIVE_AGENT: {ACTIVE_AGENT!r}")
