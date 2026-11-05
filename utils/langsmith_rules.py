"""Create online judges and automations on a tracing project.
No SDK or CLI call attaches a judge with a run filter, thread grouping or a dataset/queue action, so this uses the REST rules API.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

if TYPE_CHECKING:
    from utils.config import TracingDestination

GATEWAY_BASE_URL = "https://gateway.smith.langchain.com/v1"
MIN_THREAD_IDLE_SECONDS = 120
RULES_PATH = "/runs/rules"
WORKSPACE_PREFIX = re.compile(r"^(.*?/o/[^/]+)/")


@dataclass(frozen=True)
class RuleInfo:
    id: str
    name: str
    url: str


def judge_model(model_id: str) -> dict:
    """Serialized judge model that runs on this workspace's LLM Gateway, e.g. `openai/gpt-5.6-luna`."""
    # LangSmith swaps this for its own Gateway client at run time, so no workspace provider secret is needed.
    return {
        "lc": 1,
        "type": "constructor",
        "id": ["langchain", "chat_models", "openai", "ChatOpenAI"],
        "kwargs": {
            "model": model_id,
            "base_url": GATEWAY_BASE_URL,
            "use_responses_api": True,
            "openai_api_key": {"lc": 1, "type": "secret", "id": ["LANGSMITH_GATEWAY_API_KEY"]},
        },
    }


def project_tab_url(project_url: str, tab: Literal["evaluators", "automations"]) -> str:
    """Link to one tab of the project page, keeping any existing query parameters."""
    parts = urlsplit(project_url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "tab"]
    query.append(("tab", tab))
    return urlunsplit(parts._replace(query=urlencode(query)))


def queue_url(project_url: str, queue_id: str | UUID) -> str:
    """Link to an annotation queue in the same workspace as `project_url`."""
    match = WORKSPACE_PREFIX.match(project_url)
    if match is None:
        raise ValueError(f"No /o/<workspace>/ segment in {project_url}")
    return f"{match.group(1)}/annotation-queues/{queue_id}"


def _replace_rule(client, project: TracingDestination, body: dict) -> dict:
    """Delete rules with the same display name on the project, then create `body`."""
    # POST has no upsert, so reruns would stack duplicate rules.
    response = client.request_with_retries("GET", RULES_PATH, params={"session_id": str(project.project_id)})
    for rule in response.json():
        if rule.get("display_name") == body["display_name"]:
            client.request_with_retries("DELETE", f"{RULES_PATH}/{rule['id']}")

    response = client.request_with_retries("POST", RULES_PATH, data=json.dumps(body))
    return response.json()


def _llm_evaluator(prompt_messages: list[list[str]], schema: dict, variable_mapping: dict, model_id: str) -> dict:
    return {
        "structured": {
            "prompt": prompt_messages,
            "schema": schema,
            "variable_mapping": variable_mapping,
            "model": judge_model(model_id),
        }
    }


def upsert_judge(
    client,
    project: TracingDestination,
    *,
    name: str,
    prompt: str,
    schema: dict,
    filter: str,
    model_id: str,
    sampling_rate: float = 1.0,
) -> RuleInfo:
    """Create (or replace) an LLM judge that scores each new run matching `filter`."""
    messages = [["system", prompt], ["human", "User request:\n{{input}}\n\nAgent run:\n{{output}}"]]
    evaluator = _llm_evaluator(messages, schema, {"input": "input", "output": "output"}, model_id)
    body = {
        "display_name": name,
        "session_id": str(project.project_id),
        "sampling_rate": sampling_rate,
        "filter": filter,
        "evaluators": [evaluator],
    }
    rule = _replace_rule(client, project, body)
    return RuleInfo(id=str(rule["id"]), name=name, url=project_tab_url(project.url, "evaluators"))


def upsert_thread_judge(
    client,
    project: TracingDestination,
    *,
    name: str,
    prompt: str,
    schema: dict,
    model_id: str,
    idle_seconds: int = MIN_THREAD_IDLE_SECONDS,
) -> RuleInfo:
    """Create (or replace) an LLM judge that scores whole threads once they go idle."""
    if idle_seconds < MIN_THREAD_IDLE_SECONDS:
        raise ValueError(f"idle_seconds must be at least {MIN_THREAD_IDLE_SECONDS} (backend minimum)")

    messages = [["system", prompt], ["human", "Conversation:\n{{all_messages}}"]]
    evaluator = _llm_evaluator(messages, schema, {"all_messages": "all_messages"}, model_id)
    body = {
        "display_name": name,
        "session_id": str(project.project_id),
        "sampling_rate": 1.0,
        "group_by": "thread_id",
        "evaluators": [evaluator],
    }
    rule = _replace_rule(client, project, body)
    # The idle time is a project setting shared by every thread rule.
    client.update_project(project.project_id, project_extra={"thread_idle_seconds": idle_seconds})
    return RuleInfo(id=str(rule["id"]), name=name, url=project_tab_url(project.url, "evaluators"))


def upsert_automation(
    client,
    project: TracingDestination,
    *,
    name: str,
    filter: str,
    dataset_id: str | UUID | None = None,
    queue_id: str | UUID | None = None,
    sampling_rate: float = 1.0,
) -> RuleInfo:
    """Create (or replace) an automation that adds runs matching `filter` to a dataset or a queue."""
    if (dataset_id is None) == (queue_id is None):
        raise ValueError("Pass exactly one of dataset_id or queue_id")

    body = {
        "display_name": name,
        "session_id": str(project.project_id),
        "sampling_rate": sampling_rate,
        "filter": filter,
    }
    if dataset_id is not None:
        body["add_to_dataset_id"] = str(dataset_id)
    else:
        body["add_to_annotation_queue_id"] = str(queue_id)

    rule = _replace_rule(client, project, body)
    return RuleInfo(id=str(rule["id"]), name=name, url=project_tab_url(project.url, "automations"))
