"""Offline and fallback behavior of utils.search (no network)."""

import pytest

from utils import search


@pytest.fixture(autouse=True)
def reset_client(monkeypatch):
    monkeypatch.setattr(search, "_default_client", None)
    monkeypatch.setattr(search.time, "sleep", lambda _: None)


def _forbid_client(*args, **kwargs):
    raise AssertionError("TavilyClient must not be constructed in offline mode")


def test_no_key_returns_offline_results_without_client(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(search, "TavilyClient", _forbid_client)

    result = search.resilient_tavily_search("Microsoft quarterly earnings")

    assert result.startswith("[reference results: background, not live news]")
    assert "Azure" in result


def test_blank_key_counts_as_unset(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "  ")
    monkeypatch.setattr(search, "TavilyClient", _forbid_client)

    assert search.resilient_tavily_search("energy sector news").startswith(search.OFFLINE_TAG)


def test_placeholder_key_counts_as_unset(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "<tavily-api-key>")
    monkeypatch.setattr(search, "TavilyClient", _forbid_client)

    assert search.resilient_tavily_search("energy sector news").startswith(search.OFFLINE_TAG)


def test_client_construction_failure_falls_back(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")

    def broken_client(*args, **kwargs):
        raise RuntimeError("bad key")

    monkeypatch.setattr(search, "TavilyClient", broken_client)

    result = search.resilient_tavily_search("NVIDIA news")

    assert result.startswith("[fallback content; live search unavailable -- RuntimeError: bad key]")
    assert "Data Center" in result


def test_search_failure_falls_back_after_retries(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    calls = []

    class FailingClient:
        def search(self, query, max_results):
            calls.append(query)
            raise ConnectionError("timeout")

    result = search.resilient_tavily_search("Exxon outlook", max_retries=2, client=FailingClient())

    assert len(calls) == 3
    assert result.startswith("[fallback content")
    assert "Permian" in result


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("AAPL latest news", "Services"),
        ("JPM net interest income", "JPMorgan"),
        ("BRK.B Berkshire operating earnings", "BNSF"),
        ("GOOGL antitrust", "Google Cloud"),
        ("AGG bond ETF yield", "Bloomberg US Aggregate"),
        ("money market fund yields", "federal funds rate"),
        ("Fed interest rate decision", "FOMC"),
    ],
)
def test_ticker_and_topic_matching(query, expected):
    assert expected in search.canned_results(query)


def test_short_tickers_match_whole_words_only():
    result = search.canned_results("aggressive growth client")

    assert "Aggregate Bond" not in result


def test_multi_ticker_query_interleaves_topics():
    result = search.canned_results("NVDA GOOGL BRK.B news", max_results=3)

    assert "NVIDIA" in result and "Alphabet" in result and "Berkshire" in result


def test_unmatched_query_returns_finance_generic():
    result = search.canned_results("something unrelated entirely")

    assert "reuters.com/markets" in result
