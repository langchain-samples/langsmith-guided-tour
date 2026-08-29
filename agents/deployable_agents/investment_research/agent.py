"""Deployable investment research agent.

Internal-facing assistant for equity research analysts. Demonstrates:
- AGENTS.md for agent identity and instructions
- Skills for on-demand capabilities (research-digest, client-brief)
- Custom tools (search_research_reports, web_search)
- Two subagents (research-advisor, research-digest) rather than one
- A clarifying-question interrupt on research-advisor, on top of the
  standard file-write HITL
- CompositeBackend: FilesystemBackend for skills/AGENTS.md, StoreBackend for /memories/
"""

import os
from datetime import datetime

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_core.tools import tool
from langgraph.types import interrupt

from utils.models import model
from utils.search import resilient_tavily_search

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))


# Synthetic internal research corpus — see agents/investment_research_agent.py
# for the eval-safe twin. Duplicated rather than imported, matching this
# repo's pattern of self-contained agent modules.
_REPORTS = [
    {
        "id": "r1",
        "title": "Apple Inc. — Price Target Update Following Services Growth",
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "report_type": "price_target_update",
        "date": "2026-06-10",
        "author": "Internal Research Desk",
        "summary": "Raising price target on continued Services segment strength.",
        "full_text": (
            "We raise our price target on Apple to $265 from $245, driven by Services "
            "revenue growth outpacing hardware for the third consecutive quarter. "
            "Margin mix continues to improve as Services scales."
        ),
        "source_url": "https://research.internal/reports/r1",
    },
    {
        "id": "r2",
        "title": "Apple Inc. — Q2 FY26 Earnings Review",
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "report_type": "earnings_review",
        "date": "2026-05-02",
        "author": "Internal Research Desk",
        "summary": "EPS and revenue beat consensus; Services growth was the standout.",
        "full_text": (
            "Apple reported Q2 FY26 EPS of $1.62 vs. consensus $1.54, on revenue of "
            "$96.1B. Services revenue grew 14% YoY, ahead of the 11% Street estimate. "
            "iPhone revenue was roughly in line. Management reiterated a constructive "
            "outlook for the back half of the year."
        ),
        "source_url": "https://research.internal/reports/r2",
    },
    {
        "id": "r3",
        "title": "Apple Inc. — Follow-Up: Services Growth Durability",
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "report_type": "earnings_review",
        "date": "2026-05-15",
        "author": "Internal Research Desk",
        "summary": "Follow-up note revisiting Services growth drivers from the Q2 print.",
        "full_text": (
            "Following our initial Q2 FY26 review, we dig deeper into Services growth: "
            "App Store and subscription revenue were the primary drivers, with "
            "advertising a smaller contributor. We see this mix as durable into FY27."
        ),
        # Same URL as r2 on purpose — republished under the original earnings note.
        "source_url": "https://research.internal/reports/r2",
    },
    {
        "id": "r4",
        "title": "Apple Inc. — Initiation of Coverage",
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "report_type": "initiation",
        "date": "2025-09-01",
        "author": "Internal Research Desk",
        "summary": "Initiating at Overweight on Services mix shift and buyback pace.",
        "full_text": (
            "We initiate coverage of Apple at Overweight with a $240 price target. "
            "Our thesis rests on continued Services mix shift, disciplined capital "
            "return through buybacks, and a durable installed base. Key risks include "
            "China demand softness and regulatory pressure on App Store economics."
        ),
        "source_url": "https://research.internal/reports/r4",
    },
    {
        "id": "r5",
        "title": "ExxonMobil — Initiation of Coverage",
        "ticker": "XOM",
        "company": "ExxonMobil",
        "report_type": "initiation",
        "date": "2025-11-03",
        "author": "Internal Research Desk",
        "summary": "Initiating at Equal Weight; upstream discipline offset by refining softness.",
        "full_text": (
            "Thesis: ExxonMobil's upstream cost discipline and Permian production growth "
            "support free cash flow, but refining margins have normalized lower after "
            "the 2023-2024 peak, capping near-term earnings upside.\n\n"
            "Valuation: shares trade in line with integrated peers on forward EV/EBITDA; "
            "we see limited multiple re-rating absent a refining margin recovery.\n\n"
            "Risks: crude price volatility, refining margin compression, and execution "
            "risk on the Pioneer integration. Upside risk: faster-than-expected synergy "
            "capture from the Pioneer acquisition."
        ),
        "source_url": "https://research.internal/reports/r5",
    },
    {
        "id": "r6",
        "title": "Energy Sector Note — Refining Margins Into Year-End",
        "ticker": "XOM",
        "company": "ExxonMobil",
        "report_type": "sector_note",
        "date": "2026-03-01",
        "author": "Internal Research Desk",
        "summary": "Refining margins expected to stay range-bound through year-end.",
        "full_text": (
            "Across our integrated energy coverage, we expect refining crack spreads to "
            "stay range-bound through year-end as new capacity additions in Asia offset "
            "seasonal demand. ExxonMobil's downstream segment is most exposed within "
            "our coverage given its refining mix."
        ),
        "source_url": "https://research.internal/reports/r6",
    },
    {
        "id": "r7",
        "title": "Costco Wholesale — Q3 FY26 Earnings Review",
        "ticker": "COST",
        "company": "Costco Wholesale",
        "report_type": "earnings_review",
        "date": "2026-04-18",
        "author": "Internal Research Desk",
        "summary": "Comp sales and membership renewal rate both came in ahead of plan.",
        "full_text": (
            "Costco's Q3 FY26 comparable sales grew 6.8%, ahead of our 5.5% estimate, "
            "with membership renewal rates holding at 92.9% globally. Gross margin was "
            "roughly flat YoY as the company continues to pass through cost savings to "
            "members rather than expand margin."
        ),
        "source_url": "https://research.internal/reports/r7",
    },
    {
        "id": "r8",
        "title": "Costco Wholesale — Price Target Update",
        "ticker": "COST",
        "company": "Costco Wholesale",
        "report_type": "price_target_update",
        "date": "2026-07-01",
        "author": "Internal Research Desk",
        "summary": "Modest price target increase on membership fee increase pass-through.",
        "full_text": (
            "We raise our price target on Costco to $980 from $950 following the "
            "announced membership fee increase, which we expect to flow through to "
            "operating income with minimal impact on renewal rates based on prior "
            "fee-increase cycles."
        ),
        "source_url": "https://research.internal/reports/r8",
    },
]


@tool(parse_docstring=True)
def search_research_reports(
    query: str,
    ticker: str | None = None,
    report_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Search internal research reports by keyword and optional filters.

    Args:
        query: Free-text terms to match against title/summary/full_text.
        ticker: Filter to a specific ticker, e.g. 'AAPL'.
        report_type: One of 'initiation', 'earnings_review', 'sector_note',
            'price_target_update'.
        start_date: Only include reports on or after this ISO date.
        end_date: Only include reports on or before this ISO date.
    """
    matches = _REPORTS
    if ticker:
        matches = [r for r in matches if r["ticker"].lower() == ticker.lower()]
    if report_type:
        matches = [r for r in matches if r["report_type"] == report_type]
    if start_date:
        matches = [r for r in matches if r["date"] >= start_date]
    if end_date:
        matches = [r for r in matches if r["date"] <= end_date]
    if query:
        q = query.lower()
        matches = [
            r for r in matches
            if q in r["title"].lower() or q in r["summary"].lower() or q in r["full_text"].lower()
        ]

    if not matches:
        return "No reports matched the given query and filters."
    return "\n\n---\n\n".join(
        f"**{r['title']}** ({r['ticker']}, {r['report_type']}, {r['date']})\n"
        f"Author: {r['author']}\n"
        f"Summary: {r['summary']}\n"
        f"Full text: {r['full_text']}\n"
        f"Source: {r['source_url']}"
        for r in matches
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
def ask_clarifying_question(question: str) -> str:
    """Pause and ask the analyst a clarifying question before retrieving reports.

    Args:
        question: The question to ask, e.g. requesting a missing ticker,
            date range, or report type.
    """
    return interrupt(question)


research_advisor_subagent = {
    "name": "research-advisor",
    "description": (
        "Delegate data retrieval — internal research reports and/or external "
        "web context. Give one query at a time."
    ),
    "system_prompt": f"""You are a research-advisor agent for an investment research desk. Today is {datetime.now().strftime('%Y-%m-%d')}.
Use search_research_reports for internal report content and web_search for external market/company context. If the request has no ticker/company, date range, or report type and nothing can be inferred, call ask_clarifying_question before searching.
Limit to 3 tool calls total. Cite each source_url you draw on.""",
    "tools": [search_research_reports, web_search, ask_clarifying_question],
}

research_digest_subagent = {
    "name": "research-digest",
    "description": (
        "Delegate summarization of already-retrieved report records into a "
        "digest. Pass the retrieved report content, not a topic to search for."
    ),
    "system_prompt": """You are a research-digest agent. You have no search tools — you summarize the report content you're given.
Produce a concise digest covering key points and any rating/price-target changes, with inline citations to each source_url.
Check for a relevant skill when asked to produce a specific output format (e.g. a client brief).""",
    "tools": [],
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
    system_prompt="You are an expert investment research assistant for equity research analysts.",
    memory=["./AGENTS.md"],
    skills=["./skills/"],
    subagents=[research_advisor_subagent, research_digest_subagent],
    backend=backend,
    interrupt_on={"write_file": True, "edit_file": True},
)
