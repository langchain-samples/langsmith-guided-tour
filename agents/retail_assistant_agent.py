"""Retail shopping & service assistant — customer-facing deep agent.

A main orchestrator that routes each customer request to one of seven
specialized subagents (recommendation, availability, order status, returns,
loyalty, promotions, support escalation). All tools are mocked — they return
canned demo data, no network calls.

Mirrors research_agent.py's eval-safe shape: no HITL, no FilesystemBackend,
fresh MemorySaver per call.
"""

from deepagents import create_deep_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from utils.models import model


# Mocked storefront data — production would hit catalog / OMS / loyalty systems.
_PRODUCTS = {
    "1001": {"name": "16% Layer Poultry Feed, 50 lb", "price": 17.99,
             "category": "Livestock & Poultry", "rating": 4.7},
    "1002": {"name": "Insulated Duck Work Jacket", "price": 129.99,
             "category": "Workwear & Apparel", "rating": 4.6},
    "1003": {"name": "54 in. Zero-Turn Riding Mower", "price": 4299.99,
             "category": "Lawn & Garden", "rating": 4.4},
}

_STORE_STOCK = {"1001": 24, "1002": 6, "1003": 0}

_ORDERS = {
    "ORD-10054": {"status": "In transit", "eta": "2026-06-06",
                  "items": ["16% Layer Poultry Feed, 50 lb (x2)"],
                  "carrier": "Ground", "tracking": "1Z-MOCK-10054"},
    "ORD-10092": {"status": "Delivered", "eta": "2026-05-28",
                  "items": ["Insulated Duck Work Jacket (x1)"],
                  "carrier": "Ground", "tracking": "1Z-MOCK-10092"},
}

_LOYALTY = {
    "CUST-001": {"tier": "Silver", "points": 1450, "next_reward_at": 2000,
                 "reward_value": "$5 off"},
    "CUST-002": {"tier": "Gold", "points": 3200, "next_reward_at": 4000,
                 "reward_value": "$10 off"},
}

_PROMOTIONS = {
    "Workwear & Apparel": ["20% off select insulated jackets through 2026-06-30"],
    "Lawn & Garden": ["$300 off zero-turn riding mowers through 2026-06-15"],
    "Livestock & Poultry": ["Buy 3 get 1 free on select 50 lb feed bags"],
}

_RETURN_POLICY = {
    "general": "90-day returns with receipt for unused items in original packaging.",
    "Livestock & Poultry": "Feed and live goods are non-returnable once opened for "
                           "safety reasons; defective bags are replaced.",
    "Lawn & Garden": "Powered equipment: 30-day returns if unused, or anytime if "
                     "defective under warranty.",
}


@tool(parse_docstring=True)
def search_products(query: str) -> str:
    """Search the product catalog by keyword.

    Args:
        query: Keywords to match against product name or category.
    """
    q = query.lower()
    hits = [(sku, p) for sku, p in _PRODUCTS.items()
            if q in p["name"].lower() or q in p["category"].lower()]
    if not hits:
        return f"No products matched '{query}'. Try feed, jacket, or mower."
    return "\n".join(
        f"SKU {sku}: {p['name']} — ${p['price']:.2f} ({p['category']}, {p['rating']}★)"
        for sku, p in hits
    )


@tool(parse_docstring=True)
def check_availability(sku: str, zip_code: str) -> str:
    """Check in-store and online stock for a product.

    Args:
        sku: Product SKU. Known SKUs: 1001, 1002, 1003.
        zip_code: Customer ZIP code used to find the nearest store.
    """
    product = _PRODUCTS.get(sku)
    if product is None:
        return f"No product found with SKU '{sku}'. Known SKUs: {', '.join(_PRODUCTS)}."
    on_hand = _STORE_STOCK[sku]
    store = (f"{on_hand} in stock at store #1234 near {zip_code}"
             if on_hand else f"out of stock at store #1234 near {zip_code}")
    online = "in stock online" if on_hand else "ships from warehouse (3-5 days)"
    return f"{product['name']} (SKU {sku}): {store}; {online}."


@tool(parse_docstring=True)
def get_order_status(order_id: str) -> str:
    """Look up the status of a customer order.

    Args:
        order_id: Order identifier, e.g. 'ORD-10054'.
    """
    order = _ORDERS.get(order_id.upper())
    if order is None:
        return f"No order found with id '{order_id}'. Known orders: {', '.join(_ORDERS)}."
    return (f"Order {order_id.upper()}: {order['status']} (ETA {order['eta']}).\n"
            f"Items: {', '.join(order['items'])}\n"
            f"Carrier: {order['carrier']} — tracking {order['tracking']}")


@tool(parse_docstring=True)
def get_return_policy(category: str) -> str:
    """Return the return/exchange policy for a product category.

    Args:
        category: Product category, or 'general' for the default policy.
    """
    policy = _RETURN_POLICY.get(category, _RETURN_POLICY["general"])
    return f"{category} return policy: {policy}"


@tool(parse_docstring=True)
def get_loyalty_account(customer_id: str) -> str:
    """Look up a rewards-program account balance and tier.

    Args:
        customer_id: Customer identifier, e.g. 'CUST-001'.
    """
    acct = _LOYALTY.get(customer_id.upper())
    if acct is None:
        return f"No rewards account found for '{customer_id}'. Known accounts: {', '.join(_LOYALTY)}."
    to_next = acct["next_reward_at"] - acct["points"]
    return (f"Account {customer_id.upper()}: {acct['tier']} tier, {acct['points']} points.\n"
            f"{to_next} points to the next {acct['reward_value']} reward.")


@tool(parse_docstring=True)
def get_promotions(category: str) -> str:
    """List active promotions, optionally filtered by category.

    Args:
        category: Product category to filter by, or 'all' for everything.
    """
    if category.lower() == "all":
        return "\n".join(f"{cat}: {p}" for cat, ps in _PROMOTIONS.items() for p in ps)
    promos = _PROMOTIONS.get(category)
    if not promos:
        return f"No active promotions for '{category}'."
    return "\n".join(f"{category}: {p}" for p in promos)


@tool(parse_docstring=True)
def create_support_ticket(customer_id: str, issue: str) -> str:
    """Open a customer support ticket for a human agent to follow up.

    Args:
        customer_id: Customer identifier, e.g. 'CUST-001'.
        issue: Short description of the customer's issue.
    """
    return (f"Ticket CASE-48217 opened for {customer_id}: \"{issue}\".\n"
            "A support specialist will follow up within 1 business day.")


@tool(parse_docstring=True)
def get_support_contact() -> str:
    """Return human support contact channels and hours."""
    return ("Customer support: 1-800-555-0123, daily 8am-9pm ET.\n"
            "Live chat available in the app during the same hours.")


# The seven specialized agents the orchestrator routes to via task().
SUBAGENTS = [
    {
        "name": "product-recommendation",
        "description": "Recommend or compare products for a shopping need.",
        "system_prompt": "You recommend products. Use search_products to find options, "
                         "then suggest the best fit with a one-line reason.",
        "tools": [search_products],
    },
    {
        "name": "product-availability",
        "description": "Check whether a product is in stock in-store or online.",
        "system_prompt": "You check stock. Use check_availability with the SKU and the "
                         "customer's ZIP code.",
        "tools": [check_availability],
    },
    {
        "name": "order-status",
        "description": "Look up the status of a customer's order.",
        "system_prompt": "You report order status. Use get_order_status with the order id.",
        "tools": [get_order_status],
    },
    {
        "name": "return-policy",
        "description": "Answer return and exchange policy questions.",
        "system_prompt": "You answer returns questions. Use get_return_policy for the "
                         "relevant category; never invent exceptions.",
        "tools": [get_return_policy],
    },
    {
        "name": "loyalty-points",
        "description": "Answer rewards-program balance, tier, and reward questions.",
        "system_prompt": "You handle loyalty questions. Use get_loyalty_account with the "
                         "customer id.",
        "tools": [get_loyalty_account],
    },
    {
        "name": "promotion",
        "description": "Share current promotions and deals.",
        "system_prompt": "You share promotions. Use get_promotions, filtered by category "
                         "when one is given.",
        "tools": [get_promotions],
    },
    {
        "name": "customer-support-escalation",
        "description": "Escalate complaints or out-of-scope issues to human support.",
        "system_prompt": "You handle escalations. Open a ticket with create_support_ticket "
                         "and share contact options with get_support_contact.",
        "tools": [create_support_ticket, get_support_contact],
    },
]

ORCHESTRATOR_PROMPT = (
    "You are a retail shopping and service assistant for an online store. "
    "Interpret each customer request and route it to the right specialized subagent "
    "via the task() tool: product-recommendation, product-availability, order-status, "
    "return-policy, loyalty-points, promotion, or customer-support-escalation. "
    "Answer concisely from the subagent's result. Never invent prices, stock, orders, "
    "or points; if something isn't found, say so. Escalate complaints and out-of-scope "
    "issues to customer-support-escalation."
)


def build_retail_assistant_agent():
    """Return a fresh retail assistant deep agent.

    Each call returns a new agent with a fresh checkpointer so eval runs don't
    share state with each other.
    """
    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=ORCHESTRATOR_PROMPT,
        subagents=SUBAGENTS,
        checkpointer=MemorySaver(),
    )
