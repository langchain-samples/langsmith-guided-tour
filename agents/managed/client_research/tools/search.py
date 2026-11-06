"""Tavily web search for the managed agent."""

from langchain.tools import tool
from tavily import TavilyClient


@tool(parse_docstring=True)
def web_search(query: str) -> dict:
    """Search the web for company news, market data, or general information.

    Args:
        query: Search query to execute.
    """
    try:
        # Built per call so the deployment starts even before TAVILY_API_KEY is set.
        return TavilyClient().search(query, max_results=3)
    except Exception as error:  # quota, auth or network: a raised error would end the whole run
        return {"error": f"Web search failed: {error}", "results": []}
