"""Pins the agentevals superset behavior Module 5 relies on (no model calls)."""

from agentevals.trajectory.match import create_trajectory_match_evaluator
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

superset_match = create_trajectory_match_evaluator(
    trajectory_match_mode="superset",
    tool_args_match_mode="ignore",
    tool_args_match_overrides={"get_client_profile": ["client_id"]},
)


def _trajectory(*calls):
    messages = [HumanMessage("Request")]
    for index, (name, args) in enumerate(calls):
        call_id = f"call_{index}"
        messages.append(AIMessage("", tool_calls=[{"name": name, "args": args, "id": call_id}]))
        messages.append(ToolMessage("ok", tool_call_id=call_id))
    messages.append(AIMessage("Done."))
    return messages


LOOKUP_REFERENCE = _trajectory(("get_client_profile", {"client_id": "CL-0042"}))


def test_wrong_client_id_fails():
    result = superset_match(outputs=_trajectory(("get_client_profile", {"client_id": "acme-pension"})), reference_outputs=LOOKUP_REFERENCE)
    assert result["key"] == "trajectory_superset_match"
    assert result["score"] is False


def test_extra_lookup_tool_passes():
    outputs = _trajectory(("find_client_id", {"name": "Acme"}), ("get_client_profile", {"client_id": "CL-0042"}))
    assert superset_match(outputs=outputs, reference_outputs=LOOKUP_REFERENCE)["score"] is True


def test_other_tool_args_are_ignored():
    reference = _trajectory(("web_search", {"query": "AAPL news"}))
    outputs = _trajectory(("web_search", {"query": "Apple earnings this week"}))
    assert superset_match(outputs=outputs, reference_outputs=reference)["score"] is True
