"""Helpers for offline evaluators: read dataset messages in any stored form, and average experiment scores."""

from collections import defaultdict
from collections.abc import Iterable

from langchain_core.messages import convert_to_messages


def last_message_text(messages: list, message_type: str) -> str:
    """Return the text of the last message of a type ("human", "ai", "tool"), or "".

    Accepts live message objects, role dicts, type dicts and serialized `lc` envelopes.
    AI messages that only request tool calls are skipped, so "ai" means the final answer.
    """
    for message in reversed(convert_to_messages(messages)):
        if message.type != message_type:
            continue
        if message.type == "ai" and message.tool_calls:
            continue
        return str(message.text)
    return ""


def mean_scores(results: Iterable[dict], split: str | None = None) -> dict[str, float]:
    """Average each feedback key over experiment rows, optionally for one dataset split."""
    scores_by_key = defaultdict(list)
    for row in results:
        splits = (row["example"].metadata or {}).get("dataset_split", [])
        if split is not None and split not in splits:
            continue
        for result in row["evaluation_results"]["results"]:
            if result.score is not None:
                scores_by_key[result.key].append(float(result.score))
    return {key: round(sum(scores) / len(scores), 2) for key, scores in scores_by_key.items()}
