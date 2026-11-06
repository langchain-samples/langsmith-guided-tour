"""Deployable client-research agent: the notebook agent's tools plus AGENTS.md, skills and store-backed memories."""

import os
from datetime import datetime

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_core.language_models import BaseChatModel

from agents.client_research_agent import client_lookup_errors, get_client_profile, web_search
from utils.models import make_model

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Replays run concurrently against one container; keep the agent's own files read-only.
READ_ONLY_AGENT_FILES = FilesystemPermission(
    operations=["write"],
    paths=["/AGENTS.md", "/agent.py", "/skills/**"],
    mode="deny",
)

research_subagent = {
    "name": "research-agent",
    "description": "Delegate company / market research tasks. Give one topic at a time.",
    "system_prompt": (
        "You are a research assistant for a wealth management firm. "
        f"Today is {datetime.now().strftime('%Y-%m-%d')}.\n"
        "Use web_search to gather company news, market data, or general info. "
        "Structure findings with clear headings and inline citations. Limit to 3 search calls."
    ),
    "tools": [web_search],
}


def build_deployable_agent(model: BaseChatModel):
    """Build the deployed graph; its client tools come from the notebook agent's module."""
    backend = CompositeBackend(
        default=FilesystemBackend(root_dir=AGENT_DIR),
        routes={"/memories/": StoreBackend(namespace=lambda rt: ("client-research", "memories"))},
    )
    return create_deep_agent(
        model=model,
        tools=[web_search, get_client_profile],
        system_prompt="You are an expert client research assistant for a wealth management firm.",
        middleware=[client_lookup_errors],
        memory=["/AGENTS.md"],
        skills=["/skills/"],
        subagents=[research_subagent],
        permissions=[READ_ONLY_AGENT_FILES],
        backend=backend,
    )


agent = build_deployable_agent(make_model())
