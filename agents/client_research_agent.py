"""Client research deep agent for a wealth management firm: client profiles plus delegated web research."""

from datetime import datetime

from deepagents import create_deep_agent
from deepagents.middleware.subagents import GENERAL_PURPOSE_SUBAGENT
from langchain.agents.middleware import ToolCallRequest, ToolErrorMiddleware
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from utils.models import make_model
from utils.search import resilient_tavily_search

# Keyed by CRM client ID.
CLIENTS = {
    "CL-0042": {
        "name": "Acme Pension Fund",
        "type": "Institutional — pension",
        "aum_usd": 1_200_000_000,
        "top_holdings": [("AAPL", 0.08), ("MSFT", 0.07), ("JPM", 0.05), ("XOM", 0.04)],
        "risk_profile": "Moderate, long-duration",
        "last_meeting": "2026-02-14",
        "account_number": "ACCT-00420042",
    },
    "CL-0117": {
        "name": "Smith Family Office",
        "type": "Family office",
        "aum_usd": 85_000_000,
        "top_holdings": [("NVDA", 0.12), ("GOOGL", 0.10), ("BRK.B", 0.08)],
        "risk_profile": "Aggressive growth",
        "last_meeting": "2026-04-02",
        "account_number": "ACCT-01170117",
    },
    "CL-0263": {
        "name": "TechCorp Treasury",
        "type": "Corporate treasury",
        "aum_usd": 300_000_000,
        "top_holdings": [("US Treasuries 1-3y", 0.55), ("AGG", 0.20), ("MMF", 0.15)],
        "risk_profile": "Capital preservation",
        "last_meeting": "2026-05-01",
        "account_number": "ACCT-02630263",
    },
    "CL-0318": {
        "name": "Harbor University Endowment",
        "type": "Endowment",
        "aum_usd": 640_000_000,
        "top_holdings": [("VTI", 0.30), ("Private equity funds", 0.25), ("VXUS", 0.20), ("AGG", 0.15)],
        "risk_profile": "Moderate, perpetual horizon",
        "last_meeting": "2026-06-18",
        "account_number": "ACCT-03180318",
    },
    "CL-0405": {
        "name": "Delgado Family Trust",
        "type": "Family trust",
        "aum_usd": 42_000_000,
        "top_holdings": [("MUB", 0.35), ("VIG", 0.25), ("AAPL", 0.10)],
        "risk_profile": "Conservative income",
        "last_meeting": "2026-03-27",
        "account_number": "ACCT-04050405",
    },
}

SYSTEM_PROMPT = (
    "You are a client research assistant for a wealth management firm. "
    "Help relationship managers prep for client meetings by looking up "
    "client portfolios and researching their holdings or relevant market "
    "events. Delegate deep research topics to the research-agent."
)


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
        client_id: The client's short slug, e.g. 'acme-pension'.
    """
    client = CLIENTS.get(client_id.strip().upper())
    if client is None:
        raise ValueError(f"No client found with ID '{client_id}'.")
    holdings = "\n".join(f"  - {ticker}: {weight:.1%}" for ticker, weight in client["top_holdings"])
    return (
        f"**{client['name']}** ({client['type']})\n"
        f"Account: {client['account_number']}\n"
        f"AUM: ${client['aum_usd']:,}\n"
        f"Risk profile: {client['risk_profile']}\n"
        f"Last meeting: {client['last_meeting']}\n"
        f"Top holdings:\n{holdings}"
    )


def _client_lookup_error(exc: Exception, request: ToolCallRequest) -> str | None:
    if isinstance(exc, ValueError):
        return f"Error: {exc}"
    return None


# ToolNode re-raises plain exceptions; this returns them to the model and keeps the tool run's error status.
client_lookup_errors = ToolErrorMiddleware(_client_lookup_error, tools=[get_client_profile])


def build_client_research_agent(model=None, search_tool=None, extra_tools=()):
    """Return a fresh client-research deep agent; arguments swap the model, the search tool or add tools."""
    model = model or make_model()
    search_tool = search_tool or web_search
    research_subagent = {
        "name": "research-agent",
        "description": "Delegate company / market research tasks. Give one topic at a time.",
        "system_prompt": (
            "You are a research assistant for a wealth management firm. "
            f"Today is {datetime.now().strftime('%Y-%m-%d')}.\n"
            f"Use {search_tool.name} to gather company news, market data, or general info. "
            "Limit to 3 search calls. Cite sources."
        ),
        "tools": [search_tool],
    }
    tools = [search_tool, get_client_profile, *extra_tools]
    # The default general-purpose subagent doesn't inherit main-agent middleware, so lookup errors would crash it.
    general_purpose_subagent = {**GENERAL_PURPOSE_SUBAGENT, "tools": tools, "middleware": [client_lookup_errors]}
    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[client_lookup_errors],
        subagents=[research_subagent, general_purpose_subagent],
        checkpointer=MemorySaver(),
    )
