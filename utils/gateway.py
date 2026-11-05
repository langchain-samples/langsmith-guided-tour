"""REST plumbing for Module 6: LLM Gateway policies and Tool Gateway kits."""

import os

import httpx
from langchain_core.callbacks import BaseCallbackHandler
from langsmith.run_helpers import get_current_run_tree

API_URL = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com").rstrip("/")
POLICIES_PATH = "/v1/platform/gateway-policies"
KITS_PATH = "/v1/managed-tools/kits"
MCP_PROTOCOL_VERSION = "2025-06-18"
# langchain_core.utils._gateway.GATEWAY_METADATA_RESPONSE_KEY (private)
GATEWAY_METADATA_KEY = "lc_gateway_metadata"

KEY_TYPES = {
    "lsv2_pt_": "personal (lsv2_pt_)",
    "lsv2_sk_": "service (lsv2_sk_)",
    "lsv2_tr_": "tracing only (lsv2_tr_)",
}


class ToolGatewayError(Exception):
    """A Tool Gateway call failed."""


class ToolCallBlocked(ToolGatewayError):
    """A tool policy or the classifier denied the call."""


def _http(api_key: str, tenant_id: str | None = None) -> httpx.Client:
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id
    return httpx.Client(base_url=API_URL, headers=headers, timeout=30)


def _gateway_http() -> httpx.Client:
    # Policies apply in the org that owns the key making the model calls.
    return _http(os.environ["LANGSMITH_GATEWAY_API_KEY"])


def _tools_http() -> httpx.Client:
    return _http(os.environ["LANGSMITH_API_KEY"], tenant_id=os.environ["LANGSMITH_WORKSPACE_ID"])


def _error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text
    if not isinstance(body, dict):
        return str(body)
    return body.get("code") or body.get("detail") or body.get("error") or str(body)


def describe_key(api_key: str) -> str:
    """Label a LangSmith key by its prefix, without printing the key."""
    for prefix, label in KEY_TYPES.items():
        if api_key.startswith(prefix):
            return label
    return "unknown"


def model_endpoint(model) -> str | None:
    """Return the base URL a chat model sends its requests to."""
    return getattr(model, "openai_api_base", None) or getattr(model, "anthropic_api_url", None)


def gateway_workspace_id() -> str:
    """Return the workspace of LANGSMITH_GATEWAY_API_KEY, falling back to LANGSMITH_WORKSPACE_ID."""
    with _gateway_http() as http:
        response = http.get("/v1/platform/workspaces/current/info")
    if response.is_success:
        return response.json()["id"]
    print(f"Could not read the gateway key's workspace ({response.status_code}); using LANGSMITH_WORKSPACE_ID.")
    return os.environ["LANGSMITH_WORKSPACE_ID"]


def create_gateway_policy(policy: dict) -> dict | None:
    """Create (or upsert by matchers) a gateway policy; None when the key lacks the admin permission."""
    with _gateway_http() as http:
        response = http.post(POLICIES_PATH, json=policy)
    if response.status_code == 403:
        detail = _error_detail(response)
        print(f"Not created: {policy['name']} needs organization:gateway:manage in the gateway key's organization ({detail})")
        return None
    response.raise_for_status()
    return response.json()


def delete_gateway_policy(policy_id: str) -> None:
    """Delete a gateway policy; a policy that is already gone is fine."""
    with _gateway_http() as http:
        response = http.delete(f"{POLICIES_PATH}/{policy_id}")
    if response.status_code == 404:
        return
    response.raise_for_status()


def _find_kit_id(http: httpx.Client, name: str) -> str | None:
    cursor = None
    while True:
        params = {"page_size": 100, **({"cursor": cursor} if cursor else {})}
        response = http.get(KITS_PATH, params=params)
        response.raise_for_status()
        page = response.json()
        for kit in page["items"]:
            if kit["name"] == name:
                return kit["id"]
        cursor = page.get("next_cursor")
        if not cursor:
            return None


def create_tool_kit(name: str, tools: list[dict], scope: str = "personal") -> dict | None:
    """Return the kit named `name` with its tools, creating it if needed; None when Tool Gateway is unavailable."""
    with _tools_http() as http:
        try:
            kit_id = _find_kit_id(http, name)
            if kit_id is None:
                response = http.post(KITS_PATH, json={"name": name, "scope": scope, "tools": tools})
                response.raise_for_status()
                kit_id = response.json()["id"]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 403:
                raise
            print(f"Not created: {name} ({_error_detail(exc.response)})")
            return None
        # List and create responses omit the tool selection.
        response = http.get(f"{KITS_PATH}/{kit_id}")
    response.raise_for_status()
    return response.json()


def delete_tool_kit(kit_id: str) -> None:
    """Delete a tool kit; a kit that is already gone is fine."""
    with _tools_http() as http:
        response = http.delete(f"{KITS_PATH}/{kit_id}")
    if response.status_code == 404:
        return
    response.raise_for_status()


def _kit_error(response: httpx.Response) -> ToolGatewayError:
    body = response.json() if response.headers.get("content-type", "").endswith("json") else {}
    detail = body.get("detail") or response.text
    if response.status_code == 403 and body.get("code") == "tool_call_blocked":
        return ToolCallBlocked(detail)
    links = [cred["verification_url"] for cred in body.get("credentials", []) if cred.get("verification_url")]
    if links:
        detail = f"{detail} Connect at: {', '.join(links)}"
    return ToolGatewayError(f"{response.status_code}: {detail}")


def call_kit_tool(kit_id: str, tool_name: str, arguments: dict) -> str:
    """Call one kit tool over stateless JSON-RPC, nesting the gateway's run under the current trace."""
    headers = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
    parent_run = get_current_run_tree()
    if parent_run is not None:
        headers.update(parent_run.to_headers())
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}}

    with _tools_http() as http:
        response = http.post(f"{KITS_PATH}/{kit_id}/mcp", json=message, headers=headers)
    if not response.is_success:
        raise _kit_error(response)

    reply = response.json()
    if "error" in reply:
        raise ToolGatewayError(reply["error"].get("message", str(reply["error"])))
    result = reply["result"]
    text = "\n".join(item["text"] for item in result.get("content", []) if item.get("type") == "text")
    if result.get("isError"):
        raise ToolGatewayError(text)
    return text


class GatewayInfoCollector(BaseCallbackHandler):
    """Collect what the LLM Gateway reported about each model call in a run."""

    def __init__(self):
        self.infos: list[dict] = []

    def on_llm_end(self, response, **kwargs) -> None:
        for generations in response.generations:
            for generation in generations:
                info = (generation.generation_info or {}).get(GATEWAY_METADATA_KEY)
                if info is not None:
                    self.infos.append(info)
