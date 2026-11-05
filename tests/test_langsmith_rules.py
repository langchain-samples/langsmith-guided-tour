import json
import uuid
from types import SimpleNamespace

import pytest

from utils.langsmith_rules import (
    RuleInfo,
    judge_model,
    project_tab_url,
    queue_url,
    upsert_automation,
    upsert_judge,
    upsert_thread_judge,
)

PROJECT = SimpleNamespace(
    project_id="p-1",
    project_name="development",
    url="https://smith.langchain.com/o/t-1/projects/p/p-1",
)
SCHEMA = {
    "title": "extract",
    "description": "d",
    "type": "object",
    "properties": {"correctness": {"type": "number"}},
    "required": ["correctness"],
}
MODEL_ID = "openai/gpt-5.6-luna"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, existing_rules=()):
        self.calls = []
        self.existing_rules = list(existing_rules)
        self.project_updates = []

    def request_with_retries(self, method, pathname, **kwargs):
        self.calls.append((method, pathname, kwargs))
        if method == "GET":
            return FakeResponse(self.existing_rules)
        if method == "POST":
            return FakeResponse({"id": "rule-new", **json.loads(kwargs["data"])})
        return FakeResponse({})

    def update_project(self, project_id, *, project_extra=None):
        self.project_updates.append((project_id, project_extra))


def posted_body(client):
    posts = [call for call in client.calls if call[0] == "POST"]
    assert len(posts) == 1
    method, path, kwargs = posts[0]
    assert path == "/runs/rules"
    return json.loads(kwargs["data"])


def test_judge_model_is_portable_gateway_constructor():
    model = judge_model(MODEL_ID)
    assert model["lc"] == 1 and model["type"] == "constructor"
    assert model["id"] == ["langchain", "chat_models", "openai", "ChatOpenAI"]
    assert model["kwargs"]["model"] == MODEL_ID
    assert model["kwargs"]["base_url"] == "https://gateway.smith.langchain.com/v1"
    assert model["kwargs"]["use_responses_api"] is True
    assert model["kwargs"]["openai_api_key"] == {
        "lc": 1, "type": "secret", "id": ["LANGSMITH_GATEWAY_API_KEY"],
    }


def test_upsert_judge_posts_filtered_run_rule():
    client = FakeClient()
    rule = upsert_judge(
        client, PROJECT, name="correctness", prompt="Score it.", schema=SCHEMA,
        filter="eq(is_root, true)", model_id=MODEL_ID,
    )
    body = posted_body(client)
    assert body["display_name"] == "correctness"
    assert body["session_id"] == "p-1"
    assert body["filter"] == "eq(is_root, true)"
    assert body["sampling_rate"] == 1.0
    assert "group_by" not in body
    structured = body["evaluators"][0]["structured"]
    assert structured["prompt"][0] == ["system", "Score it."]
    assert structured["schema"] == SCHEMA
    assert structured["variable_mapping"] == {"input": "input", "output": "output"}
    assert structured["model"] == judge_model(MODEL_ID)
    assert rule == RuleInfo(
        id="rule-new", name="correctness",
        url="https://smith.langchain.com/o/t-1/projects/p/p-1?tab=evaluators",
    )


def test_upsert_replaces_rule_with_same_name_only():
    client = FakeClient(existing_rules=[
        {"id": "old-1", "display_name": "correctness"},
        {"id": "other", "display_name": "thread_resolved"},
    ])
    upsert_judge(
        client, PROJECT, name="correctness", prompt="p", schema=SCHEMA,
        filter="eq(is_root, true)", model_id=MODEL_ID,
    )
    gets = [call for call in client.calls if call[0] == "GET"]
    deletes = [call[1] for call in client.calls if call[0] == "DELETE"]
    assert gets[0][1] == "/runs/rules"
    assert gets[0][2]["params"] == {"session_id": "p-1"}
    assert deletes == ["/runs/rules/old-1"]


def test_upsert_thread_judge_groups_by_thread_and_sets_idle_time():
    client = FakeClient()
    upsert_thread_judge(
        client, PROJECT, name="thread_resolved", prompt="Resolved?", schema=SCHEMA,
        model_id=MODEL_ID, idle_seconds=120,
    )
    body = posted_body(client)
    assert body["group_by"] == "thread_id"
    assert "filter" not in body
    structured = body["evaluators"][0]["structured"]
    assert structured["variable_mapping"] == {"all_messages": "all_messages"}
    assert client.project_updates == [("p-1", {"thread_idle_seconds": 120})]


def test_thread_idle_below_backend_minimum_is_rejected():
    client = FakeClient()
    with pytest.raises(ValueError, match="120"):
        upsert_thread_judge(
            client, PROJECT, name="x", prompt="p", schema=SCHEMA,
            model_id=MODEL_ID, idle_seconds=60,
        )
    assert client.calls == []


@pytest.mark.parametrize("targets", [{}, {"dataset_id": "d-1", "queue_id": "q-1"}])
def test_upsert_automation_needs_exactly_one_action(targets):
    client = FakeClient()
    with pytest.raises(ValueError):
        upsert_automation(client, PROJECT, name="a", filter="f", **targets)
    assert client.calls == []


def test_upsert_automation_to_dataset():
    client = FakeClient()
    dataset_id = uuid.UUID(int=1)
    rule = upsert_automation(
        client, PROJECT, name="golden-correctness", filter="F", dataset_id=dataset_id,
    )
    body = posted_body(client)
    assert body["add_to_dataset_id"] == str(dataset_id)
    assert body["filter"] == "F"
    assert "add_to_annotation_queue_id" not in body
    assert "evaluators" not in body
    assert rule.url == "https://smith.langchain.com/o/t-1/projects/p/p-1?tab=automations"


def test_upsert_automation_to_queue():
    client = FakeClient()
    upsert_automation(client, PROJECT, name="review-low-correctness", filter="F", queue_id="q-1")
    body = posted_body(client)
    assert body["add_to_annotation_queue_id"] == "q-1"
    assert "add_to_dataset_id" not in body


def test_project_tab_url_keeps_existing_query():
    url = "https://smith.langchain.com/o/t-1/projects/p/p-1?env=dev"
    assert project_tab_url(url, "automations") == url + "&tab=automations"


def test_queue_url_from_project_url():
    assert queue_url(PROJECT.url, "q-9") == "https://smith.langchain.com/o/t-1/annotation-queues/q-9"


def test_queue_url_rejects_url_without_workspace():
    with pytest.raises(ValueError):
        queue_url("https://smith.langchain.com/projects/p/p-1", "q-9")
