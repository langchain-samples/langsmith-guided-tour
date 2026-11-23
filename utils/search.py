"""Tavily web search with retries and built-in offline results.

Without TAVILY_API_KEY, searches return canned finance/LangChain results tagged `[reference results: background, not live news]`.
"""

from __future__ import annotations

import os
import re
import time
from itertools import zip_longest
from typing import Optional

from tavily import TavilyClient


OFFLINE_TAG = "[reference results: background, not live news]"

Result = tuple[str, str, str]  # (title, url, content), shaped like Tavily's results[]

# Keys match whole words/phrases in the lowercased query; every matching topic contributes.
_CANNED_RESULTS: list[tuple[tuple[str, ...], list[Result]]] = [
    # --- Tickers held by the demo clients ---
    (("aapl", "apple"), [
        (
            "Apple Inc. (AAPL) — company news and quarterly results",
            "https://www.reuters.com/markets/companies/AAPL.O/",
            "Apple's results are driven by iPhone, which remains roughly half of revenue, and by "
            "Services (App Store, iCloud, Apple Music, AppleCare), its fastest-growing and "
            "highest-margin segment. Analysts watch iPhone upgrade cycles, Greater China demand, "
            "on-device AI features, and the gross-margin mix shift toward Services. Key risks "
            "include regulatory scrutiny of App Store fees, antitrust cases over default search "
            "payments, and supply-chain concentration in Asia.",
        ),
        (
            "Apple Investor Relations — financial results and capital return",
            "https://investor.apple.com/investor-relations/default.aspx",
            "Apple reports quarterly with segment revenue for iPhone, Mac, iPad, Wearables/Home/"
            "Accessories, and Services. The company runs one of the largest buyback programs in "
            "the market alongside a modest quarterly dividend, and holds a large net cash and "
            "marketable securities position.",
        ),
    ]),
    (("msft", "microsoft"), [
        (
            "Microsoft (MSFT) earnings: Azure and AI drive cloud growth",
            "https://www.reuters.com/markets/companies/MSFT.O/",
            "Microsoft's quarterly earnings are led by its Intelligent Cloud segment, where Azure "
            "growth is the metric investors watch most closely, with AI services contributing a "
            "growing share. Productivity and Business Processes (Microsoft 365, LinkedIn, "
            "Dynamics) provides steady recurring revenue. Capital expenditure on data centers "
            "has risen sharply to meet AI demand, and margins depend on how quickly that "
            "capacity is monetized.",
        ),
        (
            "Microsoft Investor Relations — earnings releases",
            "https://www.microsoft.com/en-us/investor/earnings",
            "Microsoft reports three segments: Productivity and Business Processes, Intelligent "
            "Cloud, and More Personal Computing (Windows, devices, Xbox, search). Guidance is "
            "given for the next quarter by segment on the earnings call.",
        ),
    ]),
    (("nvda", "nvidia"), [
        (
            "NVIDIA (NVDA) — data center demand anchors results",
            "https://www.reuters.com/markets/companies/NVDA.O/",
            "NVIDIA's revenue is dominated by its Data Center segment, driven by demand for AI "
            "accelerators from hyperscalers, model developers, and sovereign AI projects. "
            "Investors track supply of advanced packaging, product transitions between GPU "
            "generations, gross margin, and customer concentration. US export controls on "
            "advanced chips to China are a recurring risk to guidance.",
        ),
        (
            "NVIDIA Newsroom — financial results",
            "https://nvidianews.nvidia.com/news",
            "NVIDIA reports Data Center, Gaming, Professional Visualization, and Automotive "
            "segments. The stock is among the most volatile mega-caps; large moves around "
            "earnings are common, which matters for concentrated growth portfolios.",
        ),
    ]),
    (("jpm", "jpmorgan", "jp morgan", "jpmorgan chase"), [
        (
            "JPMorgan Chase (JPM) — earnings and net interest income outlook",
            "https://www.reuters.com/markets/companies/JPM.N/",
            "JPMorgan is the largest US bank by assets. Results hinge on net interest income, "
            "which moves with the rate path and deposit costs, plus investment banking fees, "
            "markets revenue, and credit card charge-offs. Management's NII guidance and "
            "commentary on consumer credit quality are typically the market's focus.",
        ),
        (
            "JPMorgan Chase Investor Relations",
            "https://www.jpmorganchase.com/ir",
            "JPMorgan reports four segments: Consumer & Community Banking, Commercial & "
            "Investment Bank, Asset & Wealth Management, and Corporate. It maintains a "
            "fortress balance sheet with capital well above regulatory minimums.",
        ),
    ]),
    (("xom", "exxon", "exxonmobil", "exxon mobil"), [
        (
            "Exxon Mobil (XOM) — production growth and oil price sensitivity",
            "https://www.reuters.com/markets/companies/XOM.N/",
            "Exxon's earnings track crude and natural gas prices and refining margins. Growth "
            "comes from Permian Basin and Guyana production; the company emphasizes cost cuts "
            "and disciplined capital spending. Dividends and buybacks are a core part of the "
            "investment case, though a sustained drop in oil prices would pressure cash flow.",
        ),
        (
            "ExxonMobil Investors — earnings and corporate plan",
            "https://corporate.exxonmobil.com/investors",
            "ExxonMobil reports Upstream, Energy Products, Chemical Products, and Specialty "
            "Products. Its corporate plan sets production, capex, and shareholder return "
            "targets several years out.",
        ),
    ]),
    (("googl", "goog", "alphabet", "google"), [
        (
            "Alphabet (GOOGL) — Search, YouTube, and Google Cloud",
            "https://www.reuters.com/markets/companies/GOOGL.O/",
            "Alphabet's revenue is led by Google Search advertising, with YouTube ads and "
            "subscriptions growing alongside. Google Cloud has become a meaningful profit "
            "contributor on AI infrastructure demand. Investors weigh AI competition in search, "
            "rising capex, and US antitrust remedies affecting search distribution and ad tech.",
        ),
        (
            "Alphabet Investor Relations",
            "https://abc.xyz/investor/",
            "Alphabet reports Google Services, Google Cloud, and Other Bets. The company pays a "
            "quarterly dividend and runs a large share repurchase program.",
        ),
    ]),
    (("brk.b", "brk-b", "brk b", "brk", "berkshire", "berkshire hathaway"), [
        (
            "Berkshire Hathaway (BRK.B) — operating earnings and cash pile",
            "https://www.reuters.com/markets/companies/BRKb.N/",
            "Berkshire's operating earnings come from insurance (GEICO, reinsurance), BNSF "
            "Railway, Berkshire Hathaway Energy, and manufacturing and retail businesses. It "
            "holds a very large cash and Treasury bill position and a concentrated equity "
            "portfolio. Investors watch insurance float growth, buyback activity, and "
            "leadership succession.",
        ),
        (
            "Berkshire Hathaway — annual and quarterly reports",
            "https://www.berkshirehathaway.com/reports.html",
            "Berkshire publishes quarterly 10-Q filings and an annual shareholder letter. The "
            "company does not pay a dividend; capital is retained for acquisitions, "
            "investments, and repurchases.",
        ),
    ]),
    # --- Fixed income and cash ---
    (("treasury", "treasuries", "t-bill", "t-bills", "yield curve", "bond yields", "us 1-3y"), [
        (
            "Daily Treasury Par Yield Curve Rates",
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve",
            "The US Treasury publishes daily par yields across maturities from 1 month to 30 "
            "years. Short-dated Treasuries (1-3 years) carry low duration and minimal credit "
            "risk, making them a core capital-preservation holding for corporate treasuries. "
            "Their yields move closely with expectations for the federal funds rate.",
        ),
        (
            "Treasury yields — market news",
            "https://www.reuters.com/markets/rates-bonds/",
            "Front-end Treasury yields respond most to Federal Reserve guidance and inflation "
            "data, while long-end yields also reflect growth expectations and Treasury supply. "
            "An inverted or flattening curve is often read as a signal of slower growth ahead.",
        ),
    ]),
    (("agg", "aggregate bond", "ishares core", "bond etf", "bond fund"), [
        (
            "iShares Core U.S. Aggregate Bond ETF (AGG)",
            "https://www.ishares.com/us/products/239458/ishares-core-total-us-bond-market-etf",
            "AGG tracks the Bloomberg US Aggregate Bond Index: investment-grade Treasuries, "
            "agency mortgage-backed securities, and corporate bonds, with an intermediate "
            "duration of roughly six years. It has a very low expense ratio and is widely used "
            "as a core fixed-income holding. Price falls when rates rise, offset over time by "
            "higher reinvestment yields.",
        ),
    ]),
    (("money market", "money market fund", "money market funds", "mmf", "cash management"), [
        (
            "Money market funds — investor bulletin",
            "https://www.investor.gov/introduction-investing/investing-basics/glossary/money-market-funds",
            "Money market funds invest in short-term, high-quality debt such as Treasury bills, "
            "repurchase agreements, and commercial paper. Government MMFs aim to hold a stable "
            "$1.00 share price. Yields track the federal funds rate closely, so they fall "
            "quickly when the Fed cuts. They are not FDIC insured.",
        ),
        (
            "Money market fund assets — market news",
            "https://www.reuters.com/markets/us/",
            "Corporate treasurers use government money market funds for operating cash and "
            "liquidity buffers. Flows into MMFs tend to rise when short-term yields are "
            "attractive relative to bank deposits.",
        ),
    ]),
    # --- Endowment and family trust holdings ---
    (("vti", "vxus", "total stock market", "total international", "index fund", "index funds"), [
        (
            "Vanguard Total Stock Market ETF (VTI) and Total International Stock ETF (VXUS)",
            "https://investor.vanguard.com/investment-products/etfs/profile/vti",
            "VTI holds nearly every US-listed stock, weighted by market cap, so its largest "
            "positions are the mega-cap tech names. VXUS covers developed and emerging markets "
            "outside the US. Together they give low-cost global equity exposure and are a "
            "common core for endowments with a perpetual horizon.",
        ),
    ]),
    (("private equity", "private equity funds", "private markets", "illiquid"), [
        (
            "Private equity in institutional portfolios — liquidity and valuation lag",
            "https://www.reuters.com/business/finance/",
            "Endowments hold private equity for long-term return premiums, accepting capital "
            "calls, multi-year lockups, and quarterly valuations that lag public markets. "
            "Investors watch distributions back to limited partners, secondary-market "
            "discounts, and the share of the portfolio that is illiquid.",
        ),
    ]),
    (("mub", "municipal bond", "municipal bonds", "muni", "munis"), [
        (
            "iShares National Muni Bond ETF (MUB)",
            "https://www.ishares.com/us/products/239766/ishares-national-amtfree-muni-bond-etf",
            "MUB holds investment-grade US municipal bonds whose interest is generally exempt "
            "from federal income tax, which makes it a core income holding for taxable, "
            "conservative investors. Prices fall when rates rise; credit risk is low but varies "
            "by issuer.",
        ),
    ]),
    (("vig", "dividend appreciation", "dividend growth"), [
        (
            "Vanguard Dividend Appreciation ETF (VIG)",
            "https://investor.vanguard.com/investment-products/etfs/profile/vig",
            "VIG tracks US companies with a record of growing dividends for at least ten "
            "consecutive years, excluding the highest yielders. It tilts toward quality large "
            "caps and suits income-focused clients who also want equity growth.",
        ),
    ]),
    (("endowment", "endowments", "spending rate"), [
        (
            "University endowments — spending policy and asset allocation",
            "https://www.reuters.com/business/finance/",
            "Endowments fund a fixed share of their assets each year, typically 4-5%, so they "
            "invest for a perpetual horizon with large equity and private-market allocations. "
            "Performance for a specific endowment client comes from the firm's own reporting, "
            "not public sources.",
        ),
    ]),
    # --- Sectors and macro ---
    (("energy", "energy sector", "oil", "crude", "opec", "natural gas"), [
        (
            "Energy sector news — oil, gas and OPEC+",
            "https://www.reuters.com/business/energy/",
            "Energy equities move with crude oil and natural gas prices, which are shaped by "
            "OPEC+ production decisions, US shale output, global demand from China, and "
            "geopolitical supply risks. Integrated majors have prioritized capital discipline, "
            "dividends, and buybacks over aggressive production growth.",
        ),
        (
            "Short-Term Energy Outlook",
            "https://www.eia.gov/outlooks/steo/",
            "The US Energy Information Administration publishes monthly forecasts for crude "
            "oil, gasoline, and natural gas prices, US production, and global inventories. "
            "Inventory builds generally weigh on prices; draws support them.",
        ),
    ]),
    (("fed", "federal reserve", "fomc", "interest rate", "interest rates", "rate cut",
      "rate cuts", "rate hike", "inflation", "monetary policy"), [
        (
            "Federal Open Market Committee — meeting calendars and statements",
            "https://www.federalreserve.gov/monetarypolicy/fomc.htm",
            "The FOMC meets eight times a year to set the target range for the federal funds "
            "rate. Its statement, the Summary of Economic Projections, and the Chair's press "
            "conference guide market expectations for the rate path, which drive Treasury "
            "yields, money market yields, and bank net interest income.",
        ),
        (
            "Fed policy and interest rates — market news",
            "https://www.reuters.com/markets/us/",
            "Markets price the Fed path from inflation (CPI, PCE) and labor data. Rate cuts "
            "tend to lift long-duration assets like growth stocks and bonds, while compressing "
            "yields on cash and money market funds.",
        ),
    ]),
    (("earnings", "quarterly results", "quarterly earnings", "earnings call", "guidance"), [
        (
            "Earnings season — what to watch",
            "https://www.reuters.com/markets/",
            "During earnings season, markets react to revenue and EPS versus consensus, but "
            "forward guidance and margin commentary often move stocks more than the headline "
            "beat or miss. For mega-cap tech, AI-related capex and cloud growth are the focus.",
        ),
    ]),
    (("market outlook", "outlook", "forecast", "prediction", "stock perform", "price target",
      "next month", "next quarter", "rebalance", "rebalancing"), [
        (
            "Market outlook — why short-term stock forecasts are unreliable",
            "https://www.investor.gov/introduction-investing/getting-started/asset-allocation",
            "Short-term price moves for individual stocks cannot be predicted reliably; "
            "analyst price targets span a wide range and are frequently revised. Advisors "
            "typically frame outlooks around fundamentals, valuation, and scenario ranges "
            "rather than point forecasts, and pair them with diversification and rebalancing.",
        ),
    ]),
    (("pension", "pension fund", "liability-driven", "ldi", "funded status"), [
        (
            "Pension funds — funded status and liability-driven investing",
            "https://www.reuters.com/business/finance/",
            "Corporate and public pension funds manage assets against long-dated liabilities. "
            "Funded status improves when equity markets rise or discount rates increase. Many "
            "plans use liability-driven investing (LDI) with long-duration bonds to hedge "
            "interest-rate risk, while keeping a growth allocation in equities.",
        ),
    ]),
    (("family office", "family offices", "return last quarter"), [
        (
            "Family offices — allocation trends and concentration risk",
            "https://www.reuters.com/business/finance/",
            "Family offices often run growth-oriented portfolios with concentrated positions "
            "in mega-cap tech and private investments. Periodic rebalancing back to target "
            "weights limits concentration risk. Portfolio returns for private clients are not "
            "publicly disclosed; they come from the firm's own performance reporting system.",
        ),
    ]),
    # --- LangChain topics, used by the generic research agents ---
    (("difference between langchain and langgraph", "langchain vs langgraph"), [
        (
            "LangChain vs LangGraph — when to use each",
            "https://docs.langchain.com/oss/python/concepts/products",
            "LangChain provides the high-level agent and chain abstractions (create_agent, "
            "tools, middleware) for assembling LLM applications. LangGraph is the lower-level "
            "runtime that LangChain agents compile to — a stateful graph with nodes, edges, "
            "checkpointers, and human-in-the-loop interrupts. Use LangChain when you want a "
            "ReAct-style agent in a few lines; use LangGraph when you need custom state, "
            "multi-agent topologies, or fine-grained control of the execution loop.",
        ),
    ]),
    (("create_agent", "create agent"), [
        (
            "create_agent — LangChain v1 prebuilt agent",
            "https://docs.langchain.com/oss/python/langchain/agents",
            "`create_agent(model, tools, system_prompt, middleware=...)` returns a ReAct-style "
            "agent as a compiled LangGraph. It handles the model→tool→model loop, accepts "
            "middleware for cross-cutting concerns (logging, HITL, structured output), and "
            "can be passed a checkpointer for persistence. Returned object exposes "
            ".invoke / .stream / .ainvoke and is itself a Runnable.",
        ),
    ]),
    (("langchain v1", "langchain 1.0"), [
        (
            "LangChain v1.0 release notes",
            "https://blog.langchain.com/langchain-v1/",
            "LangChain v1 introduces a redesigned agent API centered on `create_agent` and a "
            "first-class middleware system for customizing the agent loop. Other highlights: "
            "consolidated message types in langchain-core, an init_chat_model factory for "
            "provider-agnostic model loading, and improved structured output support via "
            "with_structured_output. Built on top of LangGraph for the runtime."
        ),
        (
            "Migrating to LangChain v1",
            "https://docs.langchain.com/oss/python/releases/langchain-v1",
            "v1 simplifies the agent surface area: AgentExecutor and the v0 agent constructors "
            "are replaced by `create_agent`, middleware replaces callbacks for most flows, and "
            "tool definitions remain compatible with the existing `@tool` decorator."
        ),
    ]),
    (("langgraph",), [
        (
            "LangGraph — stateful, multi-agent workflows",
            "https://docs.langchain.com/oss/python/langgraph/overview",
            "LangGraph is an open-source framework for building stateful, multi-agent "
            "applications with LLMs. You model your workflow as a StateGraph: define a "
            "TypedDict State, register nodes (Python functions) that read state and return "
            "updates, and connect them with normal or conditional edges. Built-in support for "
            "checkpointers (persistence), interrupts (human-in-the-loop), and stores "
            "(long-term memory)."
        ),
    ]),
    (("langsmith",), [
        (
            "LangSmith — observability and evaluation for LLM apps",
            "https://docs.smith.langchain.com/",
            "LangSmith is a framework-agnostic platform for tracing, evaluating, and monitoring "
            "LLM applications. Set LANGSMITH_TRACING=true and every LLM/tool/chain call lands "
            "in your project. Build datasets, run offline evaluations with `client.evaluate`, "
            "or configure online evaluators (run rules) that score new traces automatically. "
            "Annotation queues route flagged runs to human reviewers."
        ),
    ]),
    (("tavily",), [
        (
            "Tavily — search API for AI agents",
            "https://tavily.com/",
            "Tavily is a web search API optimized for AI agents and RAG pipelines. It returns "
            "ranked search results with extracted content blocks, designed to plug directly "
            "into LLM prompts. Has a Python SDK (`tavily-python`) with a simple "
            "TavilyClient.search(query, max_results=N) interface."
        ),
    ]),
]


_GENERIC_RESULTS: list[Result] = [
    (
        "US markets overview — stocks, bonds and the Fed",
        "https://www.reuters.com/markets/us/",
        "US equity performance is concentrated in mega-cap technology, where AI investment is "
        "the dominant theme. Bond yields and money market rates track expectations for the "
        "Federal Reserve's rate path. For client meetings, frame holdings by business drivers, "
        "key risks, and portfolio fit rather than short-term price calls.",
    ),
    (
        "Researching companies before you invest",
        "https://www.investor.gov/introduction-investing/getting-started/researching-investments",
        "Primary sources for company research are SEC filings (10-K, 10-Q, 8-K) on EDGAR, "
        "investor relations sites, and earnings call transcripts. Cite the source for any "
        "factual claim and flag when information may be out of date.",
    ),
]


def _format_results(results: list[Result]) -> str:
    """Match TavilyClient output formatting used everywhere else in the workshops."""
    return "\n\n".join(f"**{t}**\n{u}\n{c}" for t, u, c in results)


def _mentions(query: str, key: str) -> bool:
    # Whole-word match so "agg" doesn't hit "aggressive" and "fed" doesn't hit "federal".
    return re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", query) is not None


def canned_results(query: str, max_results: int = 3) -> str:
    """Return Tavily-formatted canned results for every topic the query mentions."""
    q = query.lower()
    matched_topics = []
    for keys, results in _CANNED_RESULTS:
        if any(_mentions(q, key) for key in keys):
            matched_topics.append(results)
    if not matched_topics:
        return _format_results(_GENERIC_RESULTS[:max_results])

    # Round-robin so a multi-ticker query gets one hit per ticker before second hits.
    interleaved = [r for group in zip_longest(*matched_topics) for r in group if r is not None]
    return _format_results(interleaved[:max_results])


def _fallback_notice(error: Exception) -> str:
    return (
        f"[fallback content; live search unavailable -- "
        f"{type(error).__name__}: {str(error)[:120]}]\n\n"
    )


# Lazy singleton — instantiated once on first call, then reused.
_default_client: Optional[TavilyClient] = None


def resilient_tavily_search(
    query: str,
    *,
    max_retries: int = 2,
    max_results: int = 3,
    base_backoff_seconds: float = 1.0,
    client: Optional[TavilyClient] = None,
) -> str:
    """Run a Tavily search with retries; fall back to canned content on failure.

    Returns a Tavily-shaped string (each result formatted as
    `**title**\\nurl\\ncontent`, joined by blank lines) so the caller can return
    it from a `@tool` function as-is. With no `client` and no TAVILY_API_KEY,
    returns offline results immediately, prefixed with `[reference results: background, not live news]`.

    Args:
        query: search query to run.
        max_retries: additional attempts after the first call. `max_retries=2`
            means up to 3 total attempts before falling back.
        max_results: passed through to `TavilyClient.search`.
        base_backoff_seconds: first retry sleeps this long; subsequent retries
            sleep `base * attempt` (linear backoff).
        client: optional TavilyClient to use. If `None`, a lazily-initialized
            module-level client is used.
    """
    global _default_client
    if client is None:
        key = os.environ.get("TAVILY_API_KEY", "").strip()
        # "<...>" is the unedited .env.example placeholder; treat it as unset.
        if not key or key.startswith("<"):
            return f"{OFFLINE_TAG}\n\n{canned_results(query, max_results)}"
        try:
            if _default_client is None:
                _default_client = TavilyClient()
        except Exception as exc:
            return _fallback_notice(exc) + canned_results(query, max_results)
        client = _default_client

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            results = client.search(query, max_results=max_results)
            hits = results.get("results", [])
            if hits:
                return "\n\n".join(
                    f"**{r['title']}**\n{r['url']}\n{r['content']}"
                    for r in hits
                )
            last_error = RuntimeError("Tavily returned 0 results")
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(base_backoff_seconds * (attempt + 1))

    return _fallback_notice(last_error) + canned_results(query, max_results)
