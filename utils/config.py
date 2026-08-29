"""Shared configuration: which agent to run against and which LangSmith project.

Edit ACTIVE_AGENT to swap workloads. Engineers adding a new use case should
register their agent here, not edit individual notebooks.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env here, not just in utils/models.py: notebooks import this module
# first and construct `Client()` before any agent is built, and langsmith's
# Client captures its api_key at init. Resolved from this file so it works
# whatever the cwd is.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

# Which agent the notebooks build/trace/evaluate against.
#   "investment_research_agent" — investment research deep agent (NB02-06 default)
#   "research_agent"            — earlier minimal research agent (kept for reference)
#   "base_research_agent"       — deployable research/writer agent (used by NB06 / deploy)
# To add a new agent: expose a build_<name>() factory under agents/,
# add a branch below, and update ACTIVE_AGENT here.
ACTIVE_AGENT = "investment_research_agent"

# LangSmith project name used across notebooks. Override per-environment via
# the LANGSMITH_PROJECT env var.
PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "langsmith-poc-investment-research")


def load_active_agent():
    """Return a freshly built instance of the active agent."""
    if ACTIVE_AGENT == "investment_research_agent":
        from agents.investment_research_agent import build_investment_research_agent
        return build_investment_research_agent()
    if ACTIVE_AGENT == "research_agent":
        from agents.research_agent import build_research_agent
        return build_research_agent()
    if ACTIVE_AGENT == "base_research_agent":
        from agents.deployable_agents.base_research_agent.agent import agent
        return agent
    raise ValueError(f"Unknown ACTIVE_AGENT: {ACTIVE_AGENT!r}")
