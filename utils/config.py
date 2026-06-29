"""Shared configuration: which agent to run against and which LangSmith project.

Edit ACTIVE_AGENT to swap workloads. Engineers adding a new use case should
register their agent here, not edit individual notebooks.
"""

import os

# Which agent the notebooks build/trace/evaluate against.
#   "partner_growth_agent"  — partner growth deep agent (NB02-06 default)
#   "research_agent"        — earlier minimal research agent (kept for reference)
#   "base_research_agent"   — deployable research/writer agent (used by NB06 / deploy)
# To add a new agent: expose a build_<name>() factory under agents/,
# add a branch below, and update ACTIVE_AGENT here.
ACTIVE_AGENT = "partner_growth_agent"

# LangSmith project name used across notebooks. Override per-environment via
# the LANGSMITH_PROJECT env var.
PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "langsmith-poc-partner-growth")


def load_active_agent():
    """Return a freshly built instance of the active agent."""
    if ACTIVE_AGENT == "partner_growth_agent":
        from agents.partner_growth_agent import build_partner_growth_agent
        return build_partner_growth_agent()
    if ACTIVE_AGENT == "research_agent":
        from agents.research_agent import build_research_agent
        return build_research_agent()
    if ACTIVE_AGENT == "base_research_agent":
        from agents.deployable_agents.base_research_agent.agent import agent
        return agent
    raise ValueError(f"Unknown ACTIVE_AGENT: {ACTIVE_AGENT!r}")
