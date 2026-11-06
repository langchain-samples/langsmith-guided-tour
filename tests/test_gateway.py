import ast
import json
import re
from pathlib import Path

import httpx
import nbformat
import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from langsmith import RunTree, tracing_context

from utils import gateway

NOTEBOOK = Path(__file__).resolve().parents[1] / "modules" / "06_govern_optional.ipynb"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("LANGSMITH_GATEWAY_API_KEY", "lsv2_pt_gw")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_pt_ws")
    monkeypatch.setenv("LANGSMITH_WORKSPACE_ID", "ws-local")


@pytest.fixture
def mock_http(monkeypatch, env):
    """Route gateway._http through a MockTransport; returns (set_handler, requests)."""
    requests = []
    state = {"handler": None}

    def transport_handler(request):
        requests.append(request)
        return state["handler"](request)

    def fake_http(api_key, tenant_id=None):
        headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
        if tenant_id:
            headers["X-Tenant-Id"] = tenant_id
        return httpx.Client(base_url=gateway.API_URL, headers=headers, transport=httpx.MockTransport(transport_handler))

    monkeypatch.setattr(gateway, "_http", fake_http)

    def set_handler(handler):
        state["handler"] = handler

    return set_handler, requests


def test_describe_key_types():
    assert gateway.describe_key("lsv2_pt_abc") == "personal (lsv2_pt_)"
    assert gateway.describe_key("lsv2_sk_abc") == "service (lsv2_sk_)"
    assert gateway.describe_key("lsv2_tr_abc") == "tracing only (lsv2_tr_)"
    assert gateway.describe_key("sk-other") == "unknown"


def test_policy_calls_use_gateway_key(mock_http):
    set_handler, requests = mock_http
    set_handler(lambda request: httpx.Response(201, json={"id": "p1", "name": "tour-x"}))
    policy = {"name": "tour-x", "policy_type": "guard"}

    created = gateway.create_gateway_policy(policy)

    assert created == {"id": "p1", "name": "tour-x"}
    request = requests[0]
    assert (request.method, request.url.path) == ("POST", "/v1/platform/gateway-policies")
    assert request.headers["X-Api-Key"] == "lsv2_pt_gw"
    assert json.loads(request.content) == policy


def test_create_gateway_policy_returns_none_on_403(mock_http, capsys):
    set_handler, _ = mock_http
    set_handler(lambda request: httpx.Response(403, json={"error": "missing organization:gateway:manage"}))

    assert gateway.create_gateway_policy({"name": "tour-x"}) is None
    assert "organization:gateway:manage" in capsys.readouterr().out


def test_gateway_workspace_id_reads_current_info(mock_http, capsys):
    set_handler, requests = mock_http
    set_handler(lambda request: httpx.Response(200, json={"id": "ws-gw"}))
    assert gateway.gateway_workspace_id() == "ws-gw"
    assert requests[0].url.path == "/v1/platform/workspaces/current/info"
    assert requests[0].headers["X-Api-Key"] == "lsv2_pt_gw"

    set_handler(lambda request: httpx.Response(403, json={"detail": "forbidden"}))
    assert gateway.gateway_workspace_id() == "ws-local"
    assert "LANGSMITH_WORKSPACE_ID" in capsys.readouterr().out


def test_delete_gateway_policy_accepts_404(mock_http):
    set_handler, requests = mock_http
    set_handler(lambda request: httpx.Response(204))
    assert gateway.delete_gateway_policy("p1") is None
    assert (requests[0].method, requests[0].url.path) == ("DELETE", "/v1/platform/gateway-policies/p1")

    set_handler(lambda request: httpx.Response(404, json={"detail": "not found"}))
    assert gateway.delete_gateway_policy("p1") is None

    set_handler(lambda request: httpx.Response(500, json={"detail": "boom"}))
    with pytest.raises(httpx.HTTPStatusError):
        gateway.delete_gateway_policy("p1")


def test_create_tool_kit_reuses_existing_name(mock_http):
    set_handler, requests = mock_http
    kit = {"id": "k1", "name": "tour-research-kit", "tools": [{"mcp_name": "parallel_web_search"}]}

    def handler(request):
        if request.url.path == "/v1/managed-tools/kits":
            return httpx.Response(200, json={"items": [{"id": "k1", "name": "tour-research-kit"}], "next_cursor": None})
        return httpx.Response(200, json=kit)

    set_handler(handler)

    assert gateway.create_tool_kit("tour-research-kit", tools=[{"builtin_server_key": "parallel"}]) == kit
    assert [r.method for r in requests] == ["GET", "GET"]
    assert requests[1].url.path == "/v1/managed-tools/kits/k1"
    assert requests[0].headers["X-Api-Key"] == "lsv2_pt_ws"
    assert requests[0].headers["X-Tenant-Id"] == "ws-local"


def test_create_tool_kit_posts_personal_scope(mock_http):
    set_handler, requests = mock_http
    tools = [{"builtin_server_key": "parallel", "tool_name": "parallel_web_search"}]
    kit = {"id": "k2", "name": "tour-research-kit", "tools": [{"mcp_name": "parallel_web_search"}]}

    def handler(request):
        if request.method == "GET" and request.url.path == "/v1/managed-tools/kits":
            return httpx.Response(200, json={"items": [], "next_cursor": None})
        if request.method == "POST":
            return httpx.Response(201, json={"id": "k2", "name": "tour-research-kit"})
        return httpx.Response(200, json=kit)

    set_handler(handler)

    assert gateway.create_tool_kit("tour-research-kit", tools=tools) == kit
    post = next(r for r in requests if r.method == "POST")
    assert json.loads(post.content) == {"name": "tour-research-kit", "scope": "personal", "tools": tools}
    assert requests[-1].url.path == "/v1/managed-tools/kits/k2"


@pytest.mark.parametrize("code", ["lmt_not_enabled", "service_keys_unsupported"])
def test_create_tool_kit_returns_none_when_unavailable(mock_http, capsys, code):
    set_handler, _ = mock_http
    set_handler(lambda request: httpx.Response(403, json={"code": code, "detail": "nope"}))

    assert gateway.create_tool_kit("tour-research-kit", tools=[]) is None
    assert code in capsys.readouterr().out


def test_delete_tool_kit(mock_http):
    set_handler, requests = mock_http
    set_handler(lambda request: httpx.Response(204))
    gateway.delete_tool_kit("k1")
    assert (requests[0].method, requests[0].url.path) == ("DELETE", "/v1/managed-tools/kits/k1")


def _kit_result(text):
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": text}]}})


def test_call_kit_tool_sends_tenant_and_trace_headers(mock_http):
    set_handler, requests = mock_http
    set_handler(lambda request: _kit_result("hits"))

    with tracing_context(parent=RunTree(name="web_search", run_type="tool")):
        found = gateway.call_kit_tool("k1", "t", {"search_queries": ["q"]})

    assert found == "hits"
    request = requests[0]
    assert (request.method, request.url.path) == ("POST", "/v1/managed-tools/kits/k1/mcp")
    assert request.headers["X-Api-Key"] == "lsv2_pt_ws"
    assert request.headers["X-Tenant-Id"] == "ws-local"
    assert request.headers["MCP-Protocol-Version"] == "2025-06-18"
    assert "langsmith-trace" in request.headers
    assert "baggage" in request.headers
    assert json.loads(request.content) == {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "t", "arguments": {"search_queries": ["q"]}},
    }


def test_call_kit_tool_without_parent_run_sends_no_trace_headers(mock_http):
    set_handler, requests = mock_http
    set_handler(lambda request: _kit_result("hits"))

    gateway.call_kit_tool("k1", "t", {})

    assert "langsmith-trace" not in requests[0].headers


def test_call_kit_tool_raises_blocked_on_policy_denial(mock_http):
    set_handler, _ = mock_http
    set_handler(lambda request: httpx.Response(403, json={"code": "tool_call_blocked", "detail": "tool call was denied by policy"}))

    with pytest.raises(gateway.ToolCallBlocked, match="tool call was denied by policy"):
        gateway.call_kit_tool("k1", "t", {})


def test_call_kit_tool_raises_on_other_errors(mock_http):
    set_handler, _ = mock_http
    set_handler(
        lambda request: httpx.Response(428, json={"detail": "connect first", "credentials": [{"verification_url": "https://x"}]})
    )
    with pytest.raises(gateway.ToolGatewayError, match="https://x") as raised:
        gateway.call_kit_tool("k1", "t", {})
    assert not isinstance(raised.value, gateway.ToolCallBlocked)

    set_handler(
        lambda request: httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "result": {"isError": True, "content": [{"type": "text", "text": "bad"}]}}
        )
    )
    with pytest.raises(gateway.ToolGatewayError, match="bad"):
        gateway.call_kit_tool("k1", "t", {})


def test_collector_reads_gateway_metadata():
    collector = gateway.GatewayInfoCollector()
    info = {"outcome": "success", "guard_redaction_applied": True}
    with_info = ChatGeneration(message=AIMessage("x"), generation_info={"lc_gateway_metadata": info})
    without_info = ChatGeneration(message=AIMessage("y"))

    collector.on_llm_end(LLMResult(generations=[[with_info], [without_info]]))

    assert collector.infos == [info]


def test_make_model_passes_default_headers():
    from utils.models import make_model

    model = make_model(default_headers={"X-Gateway-Team": "t"})
    assert model.default_headers == {"X-Gateway-Team": "t"}
    assert gateway.model_endpoint(make_model()).startswith("https://gateway.smith.langchain.com/")


def test_client_profiles_carry_account_numbers():
    from agents.client_research_agent import CLIENTS

    for record in CLIENTS.values():
        assert any(isinstance(value, str) and re.fullmatch(r"ACCT-[0-9]{8}", value) for value in record.values())


# Policy bodies in the notebook are never sent overnight, so check them against the API's documented shape.
PAIRABLE_KEYS = {"organization_id", "workspace_id", "user_id", "api_key_id"}
BUILTIN_KEYS = PAIRABLE_KEYS | {"agent_id", "agent_environment", "run_rule_id"}
REQUEST_FIELDS = {"name", "description", "subject_matchers", "policy_type", "config", "action", "priority", "enabled"}


def _notebook_policy(variable):
    """Evaluate the dict literal assigned to `variable` in the notebook, with the workspace stubbed."""
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type != "code" or f"{variable} = {{" not in cell.source:
            continue
        for node in ast.walk(ast.parse(cell.source)):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == variable:
                return eval(compile(ast.Expression(node.value), "<cell>", "eval"), {"gateway_workspace": "ws-gw"})
    raise AssertionError(f"{variable} not found in the notebook")


def _assert_matchers_pair_workspace_with_one_header(matchers):
    keys = [matcher["key"] for matcher in matchers]
    custom = [key for key in keys if key not in BUILTIN_KEYS]
    assert keys.count("workspace_id") == 1
    assert len(custom) == 1 and re.fullmatch(r"[a-z0-9_]+", custom[0])
    assert all(matcher["value"] for matcher in matchers)


@pytest.mark.skipif(not NOTEBOOK.exists(), reason="notebook not built yet")
def test_notebook_redaction_policy_matches_api_shape():
    policy = _notebook_policy("redaction_policy")
    assert set(policy) <= REQUEST_FIELDS
    assert (policy["policy_type"], policy["action"]) == ("guard", "block")
    _assert_matchers_pair_workspace_with_one_header(policy["subject_matchers"])
    config = policy["config"]
    assert config["version"] == 1
    assert set(config["detect"]) <= {"pii", "secrets", "custom"}
    custom = config["detect"]["custom"]
    assert len(custom) <= 1 and len(custom[0]["pattern"]) <= 512
    assert re.compile(custom[0]["pattern"]).groups == 0  # a capture group would redact only the group
    assert config["trace"] == {"capture_content": True}


@pytest.mark.skipif(not NOTEBOOK.exists(), reason="notebook not built yet")
def test_notebook_spend_policy_matches_api_shape():
    policy = _notebook_policy("spend_policy")
    assert set(policy) <= REQUEST_FIELDS
    assert (policy["policy_type"], policy["action"]) == ("spend_cap", "block")
    _assert_matchers_pair_workspace_with_one_header(policy["subject_matchers"])
    config = policy["config"]
    assert config["window"] in {"hourly", "daily", "weekly", "monthly"}
    assert config["limit_usd"] > 0


def test_find_user_id_matches_email(mock_http):
    set_handler, requests = mock_http
    set_handler(lambda request: httpx.Response(200, json=[
        {"email": "someone@example.com", "ls_user_id": "u-other"},
        {"email": "Me@Example.com", "ls_user_id": "u-me"},
    ]))
    assert gateway.find_user_id("me@example.com") == "u-me"
    assert requests[0].url.path == gateway.MEMBERS_PATH
    assert requests[0].headers["X-Api-Key"] == "lsv2_pt_ws"


def test_builtin_tool_action():
    assert gateway.builtin_tool_action("parallel", "parallel_web_search") == "langsmith_parallel_parallel_web_search"


def test_create_tool_policy_posts_forbid_for_one_user(mock_http):
    set_handler, requests = mock_http
    set_handler(lambda request: httpx.Response(201, json={"id": "p1", "name": "tour-block-search"}))
    policy = gateway.create_tool_policy("tour-block-search", "u-me", ["langsmith_parallel_parallel_web_search"])

    body = json.loads(requests[0].content)
    assert policy["id"] == "p1"
    assert requests[0].url.path == gateway.TOOL_POLICIES_PATH
    assert requests[0].headers["X-Tenant-Id"] == "ws-local"
    assert body["effect"] == "FORBID"
    assert body["scope"] == {"principals": [{"type": "User", "id": "u-me"}], "actions": ["langsmith_parallel_parallel_web_search"]}


def test_create_tool_policy_reuses_existing_name(mock_http):
    set_handler, _ = mock_http

    def handler(request):
        if request.method == "POST":
            return httpx.Response(409, json={"detail": "name taken"})
        return httpx.Response(200, json={"items": [{"id": "p1", "name": "tour-block-search"}], "next_cursor": None})

    set_handler(handler)
    assert gateway.create_tool_policy("tour-block-search", "u-me", ["x"])["id"] == "p1"


def test_create_tool_policy_returns_none_on_403(mock_http, capsys):
    set_handler, _ = mock_http
    set_handler(lambda request: httpx.Response(403, json={"detail": "forbidden"}))
    assert gateway.create_tool_policy("tour-block-search", "u-me", ["x"]) is None
    assert "organization:access-control:manage" in capsys.readouterr().out


def test_delete_tool_policy_accepts_404(mock_http):
    set_handler, requests = mock_http
    set_handler(lambda request: httpx.Response(404))
    gateway.delete_tool_policy("p1")
    assert requests[0].method == "DELETE"
    assert requests[0].url.path == f"{gateway.TOOL_POLICIES_PATH}/p1"

