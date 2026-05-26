"""Deployable client research agent.

Internal-facing knowledge agent for a wealth management firm. Demonstrates:
- AGENTS.md for agent identity and instructions
- Skills for on-demand capabilities (client-brief, portfolio-update)
- Custom tools (web_search, get_client_profile)
- Research subagent for delegated work
- CompositeBackend: FilesystemBackend for skills/AGENTS.md, StoreBackend for /memories/
"""

import os
from datetime import datetime

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_core.tools import tool

from utils.models import model
from utils.search import resilient_tavily_search

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))


# Stub client data — production would hit a CRM / portfolio system.
_CLIENTS = {
    "acme-pension": {
        "name": "Acme Pension Fund",
        "type": "Institutional — pension",
        "aum_usd": 1_200_000_000,
        "top_holdings": [("AAPL", 0.08), ("MSFT", 0.07), ("JPM", 0.05), ("XOM", 0.04)],
        "risk_profile": "Moderate, long-duration",
        "last_meeting": "2026-02-14",
    },
    "smith-family-office": {
        "name": "Smith Family Office",
        "type": "Family office",
        "aum_usd": 85_000_000,
        "top_holdings": [("NVDA", 0.12), ("GOOGL", 0.10), ("BRK.B", 0.08)],
        "risk_profile": "Aggressive growth",
        "last_meeting": "2026-04-02",
    },
    "techcorp-treasury": {
        "name": "TechCorp Treasury",
        "type": "Corporate treasury",
        "aum_usd": 300_000_000,
        "top_holdings": [("US Treasuries 1-3y", 0.55), ("AGG", 0.20), ("MMF", 0.15)],
        "risk_profile": "Capital preservation",
        "last_meeting": "2026-05-01",
    },
}


@tool(parse_docstring=True)
def web_search(query: str) -> str:
    """Search the web for company news, market data, or general information.

    Args:
        query: Search query to execute.
    """
    # Retries on Tavily failure, then falls back to a canned response. See utils/search.py.
    return resilient_tavily_search(query, max_retries=2)


@tool(parse_docstring=True)
def get_client_profile(client_id: str) -> str:
    """Look up a client's profile, holdings, and risk metadata.

    Args:
        client_id: Short client identifier. Known IDs: 'acme-pension',
            'smith-family-office', 'techcorp-treasury'.
    """
    client = _CLIENTS.get(client_id.lower())
    if client is None:
        known = ", ".join(_CLIENTS.keys())
        return f"No client found with id '{client_id}'. Known clients: {known}"
    holdings = "\n".join(
        f"  - {ticker}: {weight:.1%}" for ticker, weight in client["top_holdings"]
    )
    return (
        f"**{client['name']}** ({client['type']})\n"
        f"AUM: ${client['aum_usd']:,}\n"
        f"Risk profile: {client['risk_profile']}\n"
        f"Last meeting: {client['last_meeting']}\n"
        f"Top holdings:\n{holdings}"
    )


research_subagent = {
    "name": "research-agent",
    "description": "Delegate company / market research tasks. Give one topic at a time.",
    "system_prompt": f"""You are a research assistant for a wealth management firm. Today is {datetime.now().strftime('%Y-%m-%d')}.
Use web_search to gather company news, market data, or general info. Structure findings with clear headings and inline citations.
Limit to 3 search calls.""",
    "tools": [web_search],
}


def backend_factory(rt):
    """FilesystemBackend for disk access, /memories/ routed to StoreBackend."""
    return CompositeBackend(
        default=FilesystemBackend(root_dir=AGENT_DIR, virtual_mode=True),
        routes={"/memories/": StoreBackend()},
    )


agent = create_deep_agent(
    model=model,
    tools=[web_search, get_client_profile],
    system_prompt="You are an expert client research assistant for a wealth management firm.",
    memory=["./AGENTS.md"],
    skills=["./skills/"],
    subagents=[research_subagent],
    backend=backend_factory,
)
