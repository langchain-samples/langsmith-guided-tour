"""Deployable partner growth agent.

Merchant-facing sales agent for a retail-media platform. Demonstrates:
- AGENTS.md for agent identity and instructions
- Skills for on-demand capabilities (account-brief, outreach-email)
- Custom tools (web_search, get_merchant_profile, score_merchant_fit)
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


# Stub merchant data — production would hit a CRM / merchant platform.
_MERCHANTS = {
    "apex-apparel": {
        "name": "Apex Apparel",
        "category": "Apparel & Footwear",
        "annual_online_gmv_usd": 500_000_000,
        "gross_margin_pct": 55,
        "current_channels": ["paid_search", "affiliate"],
        "monthly_digital_ad_spend_usd": 2_000_000,
        "attribution_maturity": "MMM + incrementality",
        "last_touchpoint": "2026-05-20: Intro call, interested in affiliate expansion",
        "recent_signals": [
            "2026-05: Expanded same-day delivery to 12 new metros",
            "2026-Q1: DTC revenue up 18% YoY; launched a paid loyalty tier",
        ],
    },
    "lumina-beauty": {
        "name": "Lumina Beauty",
        "category": "DTC Beauty",
        "annual_online_gmv_usd": 200_000_000,
        "gross_margin_pct": 70,
        "current_channels": ["paid_search", "paid_social", "affiliate"],
        "monthly_digital_ad_spend_usd": 3_000_000,
        "attribution_maturity": "MMM + incrementality",
        "last_touchpoint": "2026-06-01: Asked about co-op ad opportunities",
        "recent_signals": [
            "2026-06: Launched a creator / affiliate storefront program",
            "2026-Q1: Opened first EU fulfillment center; international sales +30%",
        ],
    },
    "nestwell-home": {
        "name": "Nestwell Home",
        "category": "Home Goods",
        "annual_online_gmv_usd": 150_000_000,
        "gross_margin_pct": 35,
        "current_channels": ["affiliate"],
        "monthly_digital_ad_spend_usd": 400_000,
        "attribution_maturity": "last-click",
        "last_touchpoint": "2026-04-10: Evaluating affiliate ROI",
        "recent_signals": [
            "2026-04: Piloting a furniture trade-in / resale program",
            "2026-Q1: Shifted budget from paid social to affiliate after an ROI review",
        ],
    },
    "voltedge-electronics": {
        "name": "VoltEdge Electronics",
        "category": "Consumer Electronics",
        "annual_online_gmv_usd": 1_000_000_000,
        "gross_margin_pct": 8,
        "current_channels": ["paid_search"],
        "monthly_digital_ad_spend_usd": 5_000_000,
        "attribution_maturity": "last-click",
        "last_touchpoint": "2026-03-15: Raised margin concerns on commission model",
        "recent_signals": [
            "2026-05: Cutting low-ROI ad spend amid electronics price wars",
            "2026-Q1: Opened a third-party seller marketplace",
        ],
    },
    "maison-lux": {
        "name": "Maison Lux",
        "category": "Luxury Fashion",
        "annual_online_gmv_usd": 40_000_000,
        "gross_margin_pct": 65,
        "current_channels": [],
        "monthly_digital_ad_spend_usd": 100_000,
        "attribution_maturity": "none",
        "last_touchpoint": "2026-02-28: Brand-led, skeptical of performance",
        "recent_signals": [
            "2026-03: New brand campaign with a fashion house; no performance channels",
            "2026-Q1: Relaunched flagship site around invite-only product drops",
        ],
    },
    "cedar-corner": {
        "name": "Cedar & Corner",
        "category": "Regional Home Décor",
        "annual_online_gmv_usd": 12_000_000,
        "gross_margin_pct": 45,
        "current_channels": [],
        "monthly_digital_ad_spend_usd": 0,
        "attribution_maturity": "none",
        "last_touchpoint": "2026-01-12: Early, no digital acquisition yet",
        "recent_signals": [
            "2026-02: Opened first online store; no paid acquisition yet",
            "2026-Q1: Hired its first head of e-commerce",
        ],
    },
}

_PERF_CHANNELS = {"paid_search", "paid_social", "affiliate"}


def _score_levers(m: dict) -> list[tuple[str, str, int, str]]:
    """Return (lever, rating, points, note) for each of the four fit levers."""
    gmv = m["annual_online_gmv_usd"]
    if gmv >= 200_000_000:
        vol = ("High", 2)
    elif gmv >= 50_000_000:
        vol = ("Med", 1)
    else:
        vol = ("Low", 0)

    margin = m["gross_margin_pct"]
    if margin >= 40:
        mar = ("High", 2)
    elif margin >= 20:
        mar = ("Med", 1)
    else:
        mar = ("Low", 0)

    has_perf = bool(_PERF_CHANNELS.intersection(m["current_channels"]))
    spend = m["monthly_digital_ad_spend_usd"]
    if has_perf and spend >= 1_000_000:
        acq = ("High", 2)
    elif has_perf or spend >= 250_000:
        acq = ("Med", 1)
    else:
        acq = ("Low", 0)

    roi = {"MMM + incrementality": ("High", 2), "last-click": ("Med", 1)}.get(
        m["attribution_maturity"], ("Low", 0)
    )

    return [
        ("Online volume", *vol, f"${gmv:,} annual online GMV"),
        ("Margin headroom", *mar, f"{margin}% gross margin"),
        ("Digital-acquisition readiness", *acq,
         f"{', '.join(m['current_channels']) or 'no perf channels'}; ${spend:,}/mo ad spend"),
        ("ROI / attribution orientation", *roi, m["attribution_maturity"]),
    ]


@tool(parse_docstring=True)
def web_search(query: str) -> str:
    """Search the web for merchant news, category trends, or growth signals.

    Args:
        query: Search query to execute.
    """
    # Retries on Tavily failure, then falls back to a canned response. See utils/search.py.
    return resilient_tavily_search(query, max_retries=2)


@tool(parse_docstring=True)
def get_merchant_profile(merchant_id: str) -> str:
    """Look up a merchant's account profile: category, online GMV, margin, channels, attribution.

    Args:
        merchant_id: Short merchant identifier. Known IDs: 'apex-apparel',
            'lumina-beauty', 'nestwell-home', 'voltedge-electronics',
            'maison-lux', 'cedar-corner'.
    """
    m = _MERCHANTS.get(merchant_id.lower())
    if m is None:
        known = ", ".join(_MERCHANTS.keys())
        return f"No merchant found with id '{merchant_id}'. Known merchants: {known}"
    signals = "\n".join(f"  - {s}" for s in m["recent_signals"])
    return (
        f"**{m['name']}** ({m['category']})\n"
        f"Annual online GMV: ${m['annual_online_gmv_usd']:,}\n"
        f"Gross margin: {m['gross_margin_pct']}%\n"
        f"Current channels: {', '.join(m['current_channels']) or 'none (brand-only)'}\n"
        f"Monthly digital ad spend: ${m['monthly_digital_ad_spend_usd']:,}\n"
        f"Attribution maturity: {m['attribution_maturity']}\n"
        f"Last touchpoint: {m['last_touchpoint']}\n"
        f"Recent signals:\n{signals}"
    )


@tool(parse_docstring=True)
def score_merchant_fit(merchant_id: str) -> str:
    """Score a merchant's fit for performance / affiliate marketing across four levers.

    Levers: online volume, margin headroom, digital-acquisition readiness, and
    ROI/attribution orientation. Returns a tier (Strong / Moderate / Weak), the
    per-lever ratings, and a recommended pitch angle.

    Args:
        merchant_id: Short merchant identifier (see get_merchant_profile).
    """
    m = _MERCHANTS.get(merchant_id.lower())
    if m is None:
        known = ", ".join(_MERCHANTS.keys())
        return f"No merchant found with id '{merchant_id}'. Known merchants: {known}"

    levers = _score_levers(m)
    total = sum(points for _, _, points, _ in levers)
    tier = "Strong" if total >= 6 else "Moderate" if total >= 4 else "Weak"

    lines = "\n".join(f"  - {name}: {rating} — {note}" for name, rating, _, note in levers)

    # Margin is a hard constraint on commission-funded programs; flag it explicitly.
    low_margin = m["gross_margin_pct"] < 20
    if tier == "Strong":
        angle = "Lead with affiliate/performance expansion and an incrementality test."
    elif tier == "Moderate" and low_margin:
        angle = ("High volume but thin margin — anchor on a low-commission, high-efficiency "
                 "program and prove incremental ROI before scaling spend.")
    elif tier == "Moderate":
        angle = "Pitch a measured pilot with clear attribution before scaling co-op spend."
    else:
        angle = ("Weak fit today — nurture: educate on trackable acquisition and revisit once "
                 "online volume or attribution maturity grows.")

    return (
        f"**{m['name']} — Fit: {tier}** ({total}/8)\n"
        f"{lines}\n"
        f"Recommended angle: {angle}"
    )


research_subagent = {
    "name": "research-agent",
    "description": "Delegate retail-media category / industry research tasks. Give one topic at a time.",
    "system_prompt": f"""You are a research assistant for a retail-media sales team. Today is {datetime.now().strftime('%Y-%m-%d')}.
Use web_search to gather retail-media category trends, benchmarks, and competitive / industry context — not facts about a specific merchant by name (those come from the merchant profile). Structure findings with clear headings and inline citations.
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
    tools=[web_search, get_merchant_profile, score_merchant_fit],
    system_prompt="You are an expert partner growth assistant for a retail-media platform.",
    memory=["./AGENTS.md"],
    skills=["./skills/"],
    subagents=[research_subagent],
    backend=backend_factory,
    interrupt_on={"write_file": True, "edit_file": True},
)
