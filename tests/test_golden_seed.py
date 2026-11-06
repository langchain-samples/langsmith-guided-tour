"""Shape and consistency checks for data/golden_seed.json (no model calls)."""

import json
from pathlib import Path

from langchain_core.messages import convert_to_messages

from agents.client_research_agent import CLIENTS, get_client_profile

SEED = json.loads((Path(__file__).resolve().parents[1] / "data" / "golden_seed.json").read_text())
LOOKUPS = [example for example in SEED if example.get("split") == "client-lookup"]


def test_every_example_has_messages_in_and_an_answer_out():
    for example in SEED:
        assert set(example) <= {"inputs", "reference_outputs", "split", "metadata"}
        assert example["metadata"]["source"] == "golden-seed"
        assert convert_to_messages(example["inputs"]["messages"])[-1].type == "human"
        assert convert_to_messages(example["reference_outputs"]["messages"])[-1].type == "ai"


def test_base_examples_have_no_split():
    base = [example for example in SEED if "split" not in example]
    assert len(base) == 8


def test_lookups_name_the_client_never_the_id():
    assert len(LOOKUPS) == 3
    for example in LOOKUPS:
        question = example["inputs"]["messages"][0]["content"]
        client_id = convert_to_messages(example["reference_outputs"]["messages"])[1].tool_calls[0]["args"]["client_id"]
        assert CLIENTS[client_id]["name"] in question
        assert not any(known_id in question for known_id in CLIENTS)


def test_lookup_references_match_the_real_tool():
    for example in LOOKUPS:
        messages = convert_to_messages(example["reference_outputs"]["messages"])
        call = messages[1].tool_calls[0]
        assert call["name"] == "get_client_profile"
        assert messages[2].content == get_client_profile.invoke(call["args"])
