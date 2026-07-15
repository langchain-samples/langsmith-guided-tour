"""Deployable conversational data agent.

Internal-facing agent for a data/analytics team. Demonstrates:
- AGENTS.md for agent identity and instructions
- Skills for on-demand capabilities (data-brief, metric-definition)
- Custom tools (web_search, search_catalog)
- Research subagent for delegated work
- CompositeBackend: FilesystemBackend for skills/AGENTS.md, StoreBackend for /memories/
- Human-in-the-loop on file writes
"""

import os
import re
from datetime import datetime

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_core.tools import tool

from utils.models import model
from utils.search import resilient_tavily_search

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))


# Stub data-catalog entries — production would hit a metadata / catalog service.
_DATASETS = {
    "card-txn-daily": {
        "name": "Card Transactions — Daily",
        "domain": "Card",
        "owner": "Card Data Engineering",
        "classification": "Confidential",
        "freshness": "Daily by 06:00 ET",
        "key_metrics": [
            ("gross_spend", "Sum of settled purchase amounts, in USD"),
            ("active_accounts", "Distinct accounts with >= 1 posted transaction that day"),
            ("avg_ticket", "gross_spend / posted transaction count"),
        ],
    },
    "credit-risk-scores": {
        "name": "Credit Risk Scores — Monthly",
        "domain": "Risk",
        "owner": "Model Risk Management",
        "classification": "Restricted — PII (MRM approval required)",
        "freshness": "Monthly, 3rd business day",
        "key_metrics": [
            ("pd_score", "Model probability of default over 12 months, 0.0–1.0"),
            ("risk_tier", "Bucketed pd_score: A (lowest) through E (highest)"),
        ],
    },
    "marketing-campaign-perf": {
        "name": "Marketing Campaign Performance",
        "domain": "Marketing",
        "owner": "Growth Analytics",
        "classification": "Internal",
        "freshness": "Hourly",
        "key_metrics": [
            ("ctr", "Clicks / impressions"),
            ("cost_per_acquisition", "Campaign spend / approved applications"),
            ("approved_apps", "Count of approved applications attributed to the campaign"),
        ],
    },
}


@tool(parse_docstring=True)
def web_search(query: str) -> str:
    """Search the web for regulatory definitions, benchmarks, or general information.

    Args:
        query: Search query to execute.
    """
    # Retries on Tavily failure, then falls back to a canned response. See utils/search.py.
    return resilient_tavily_search(query, max_retries=2)


def _format_entry(dataset_id: str, dataset: dict) -> str:
    """Render a catalog entry as grounded, citable text."""
    metrics = "\n".join(
        f"  - {metric}: {definition}" for metric, definition in dataset["key_metrics"]
    )
    return (
        f"**{dataset['name']}** (`{dataset_id}`)\n"
        f"Domain: {dataset['domain']}\n"
        f"Owner: {dataset['owner']}\n"
        f"Classification: {dataset['classification']}\n"
        f"Freshness: {dataset['freshness']}\n"
        f"Key metrics:\n{metrics}"
    )


# Dropped from queries so common words don't cause spurious matches — a stand-in
# for the stopword handling a real embedding/BM25 retriever does for you.
_STOPWORDS = frozenset(
    "and are the was were has had have how who why you your our its for with about give tell get "
    "does did can could should would will most next this that these those than then there here "
    "what when where which whom whose".split()
)


def _searchable_text(dataset_id: str, dataset: dict) -> str:
    """Concatenate the fields a query can match against."""
    parts = [dataset_id, dataset["name"], dataset["domain"], dataset["owner"], dataset["classification"]]
    parts += [metric for metric, _ in dataset["key_metrics"]]
    parts += [definition for _, definition in dataset["key_metrics"]]
    return " ".join(parts)


@tool(parse_docstring=True)
def search_catalog(query: str) -> str:
    """Search the internal data catalog for datasets relevant to a query.

    Args:
        query: Natural-language description of the data you're looking for.
    """
    # Mocked retrieval: keyword-overlap scoring over each entry's searchable
    # text, returning the top matches' full metadata. Production swaps this for
    # vector search over embedded catalog docs — the contract (query in, ranked
    # entries out) is unchanged.
    terms = {t for t in re.findall(r"[a-z0-9_]+", query.lower()) if len(t) > 2 and t not in _STOPWORDS}
    scored = []
    for dataset_id, dataset in _DATASETS.items():
        tokens = set(re.findall(r"[a-z0-9_]+", _searchable_text(dataset_id, dataset).lower()))
        hits = len(terms & tokens)
        if hits:
            scored.append((hits, dataset_id, dataset))
    if not scored:
        known = ", ".join(_DATASETS)
        return f"No datasets in the catalog matched '{query}'. Known datasets: {known}"
    scored.sort(key=lambda s: -s[0])  # stable: ties keep catalog order
    return "\n\n".join(_format_entry(did, d) for _, did, d in scored[:3])


research_subagent = {
    "name": "research-agent",
    "description": "Delegate multi-dataset exploration or external research. Give one topic at a time.",
    "system_prompt": f"""You are a data research assistant for an analytics team. Today is {datetime.now().strftime('%Y-%m-%d')}.
Use search_catalog to find relevant catalog entries and web_search for external definitions or benchmarks. Structure findings with clear headings and inline citations.
Limit to 3 tool calls.""",
    "tools": [search_catalog, web_search],
}


def backend_factory(rt):
    """FilesystemBackend for disk access, /memories/ routed to StoreBackend."""
    return CompositeBackend(
        default=FilesystemBackend(root_dir=AGENT_DIR, virtual_mode=True),
        routes={"/memories/": StoreBackend()},
    )


# The supervisor holds only search_catalog; web_search lives in the
# research-agent, so external research is always delegated.
agent = create_deep_agent(
    model=model,
    tools=[search_catalog],
    system_prompt="You are an expert conversational data assistant for internal analysts.",
    memory=["./AGENTS.md"],
    skills=["./skills/"],
    subagents=[research_subagent],
    backend=backend_factory,
    interrupt_on={"write_file": True, "edit_file": True},
)
