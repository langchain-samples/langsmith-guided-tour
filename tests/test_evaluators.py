"""Deterministic checks for the offline-eval helpers (no model calls)."""

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langsmith.evaluation.evaluator import EvaluationResult

from utils.evaluators import last_message_text, mean_scores

LOOKUP_CALL = {"name": "get_client_profile", "args": {"client_id": "CL-0042"}, "id": "call_1", "type": "tool_call"}

# Shape of a run's outputs after LangSmith serializes it into a dataset example.
SERIALIZED = [
    {"type": "human", "content": "Profile for Acme?"},
    {"type": "ai", "content": "", "tool_calls": [LOOKUP_CALL]},
    {"type": "tool", "content": "**Acme Pension Fund**", "tool_call_id": "call_1", "name": "get_client_profile", "status": "success"},
    {"type": "ai", "content": [{"type": "text", "text": "Acme holds AAPL.", "annotations": []}]},
]


def test_final_answer_from_serialized_outputs():
    assert last_message_text(SERIALIZED, "ai") == "Acme holds AAPL."


def test_request_from_role_dict_inputs():
    assert last_message_text([{"role": "user", "content": "Profile for Acme?"}], "human") == "Profile for Acme?"


def test_constructor_envelope():
    envelope = [{"lc": 1, "type": "constructor", "id": ["langchain", "schema", "messages", "AIMessage"], "kwargs": {"content": "Done."}}]
    assert last_message_text(envelope, "ai") == "Done."


def test_live_messages_skip_tool_call_turns():
    messages = [
        HumanMessage("Profile for Acme?"),
        AIMessage("Checking.", tool_calls=[LOOKUP_CALL]),
        ToolMessage("Error: no client", tool_call_id="call_1", status="error"),
    ]
    assert last_message_text(messages, "ai") == ""


def _row(split, scores, metadata=True):
    example = SimpleNamespace(metadata={"dataset_split": [split]} if metadata else None)
    results = [EvaluationResult(key=key, score=score) for key, score in scores.items()]
    return {"run": None, "example": example, "evaluation_results": {"results": results}}


ROWS = [
    _row("base", {"correctness": 1.0, "tool_errors": 0, "trajectory_superset_match": True}),
    _row("client-lookup", {"correctness": 0.0, "tool_errors": 3, "trajectory_superset_match": False}),
    _row("base", {"correctness": None}, metadata=False),
]


def test_mean_scores_all_rows():
    assert mean_scores(ROWS) == {"correctness": 0.5, "tool_errors": 1.5, "trajectory_superset_match": 0.5}


def test_mean_scores_one_split():
    assert mean_scores(ROWS, split="client-lookup") == {"correctness": 0.0, "tool_errors": 3.0, "trajectory_superset_match": 0.0}
