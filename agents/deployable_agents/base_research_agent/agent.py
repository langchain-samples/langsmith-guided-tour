"""Deployable research agent used by Module 3.

Demonstrates:
- AGENTS.md for agent identity and instructions
- Skills for on-demand capabilities (LinkedIn, Twitter)
- Custom tools (Tavily search)
- Research subagent for delegated work
- CompositeBackend: FilesystemBackend for skills/AGENTS.md, StoreBackend for /memories/
- Human-in-the-loop on file writes
"""

import os
from datetime import datetime

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_core.tools import tool

from utils.models import model
from utils.search import resilient_tavily_search

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))


@tool(parse_docstring=True)
def tavily_search(query: str) -> str:
    """Search the web for information on a given query.

    Args:
        query: Search query to execute.
    """
    # Resilient wrapper: retries on Tavily failure, then falls back to a
    # topic-matched canned response. See utils/search.py.
    return resilient_tavily_search(query, max_retries=2)


research_subagent = {
    "name": "research-agent",
    "description": "Delegate research tasks. Give one topic at a time.",
    "system_prompt": f"""You are a research assistant. Today is {datetime.now().strftime('%Y-%m-%d')}.
Use tools to gather information. Structure findings with clear headings and inline citations.
Limit to 3 search calls.""",
    "tools": [tavily_search],
}


# An initialized instance, not a factory -- deepagents 0.7 removed backend
# factories. FilesystemBackend for disk access, /memories/ to StoreBackend.
backend = CompositeBackend(
    default=FilesystemBackend(root_dir=AGENT_DIR, virtual_mode=True),
    routes={
        # namespace is required as of deepagents 0.7; accepted by 0.6 too.
        "/memories/": StoreBackend(namespace=lambda rt: ("memories", "shared")),
    },
)


agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt="You are an expert research assistant.",
    memory=["./AGENTS.md"],
    skills=["./skills/"],
    subagents=[research_subagent],
    backend=backend,
    interrupt_on={"write_file": True, "edit_file": True},
)
