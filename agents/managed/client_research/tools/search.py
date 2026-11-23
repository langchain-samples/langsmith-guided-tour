"""Tavily web search for the managed agent; without TAVILY_API_KEY it returns built-in offline results."""

import os

from langchain.tools import tool
from tavily import TavilyClient

# Same tag as utils/search.py, which this deployable folder can't import.
OFFLINE_TAG = "[reference results: background, not live news]"

_OFFLINE_RESULTS = {
    "microsoft": {
        "title": "Microsoft (MSFT) earnings: Azure and AI drive cloud growth",
        "url": "https://www.reuters.com/markets/companies/MSFT.O/",
        "content": "Microsoft's results are led by Azure growth, with AI services a growing share. "
        "Data center capex has risen sharply to meet AI demand, and margins depend on how quickly "
        "that capacity is monetized.",
    },
    "nvidia": {
        "title": "NVIDIA (NVDA) — data center demand anchors results",
        "url": "https://www.reuters.com/markets/companies/NVDA.O/",
        "content": "NVIDIA's revenue is dominated by Data Center sales of AI accelerators. Investors "
        "track supply, product transitions, gross margin, and US export controls on chips to China.",
    },
    "apple": {
        "title": "Apple Inc. (AAPL) — company news and quarterly results",
        "url": "https://www.reuters.com/markets/companies/AAPL.O/",
        "content": "Apple's results are driven by iPhone and by Services, its fastest-growing, "
        "highest-margin segment. Risks include App Store regulation and supply-chain concentration.",
    },
}
_ALIASES = {"msft": "microsoft", "nvda": "nvidia", "aapl": "apple"}

_GENERIC_RESULT = {
    "title": "US markets overview — stocks, bonds and the Fed",
    "url": "https://www.reuters.com/markets/us/",
    "content": "US equity performance is concentrated in mega-cap technology, where AI investment is "
    "the dominant theme. Bond and money market yields track the Federal Reserve's rate path.",
}


def _offline_search(query: str) -> dict:
    words = {word.strip("?.,'\"").removesuffix("'s") for word in query.lower().split()}
    topics = {_ALIASES.get(word, word) for word in words} & _OFFLINE_RESULTS.keys()
    results = [_OFFLINE_RESULTS[topic] for topic in sorted(topics)] or [_GENERIC_RESULT]
    return {"query": query, "note": OFFLINE_TAG, "results": results}


@tool(parse_docstring=True)
def web_search(query: str) -> dict:
    """Search the web for company news, market data, or general information.

    Args:
        query: Search query to execute.
    """
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    # "<...>" is the unedited .env.example placeholder.
    if not key or key.startswith("<"):
        return _offline_search(query)
    try:
        # Built per call so the deployment starts even before TAVILY_API_KEY is set.
        return TavilyClient().search(query, max_results=3)
    except Exception as error:  # quota, auth or network: a raised error would end the whole run
        return {"error": f"Web search failed: {error}", "results": []}
