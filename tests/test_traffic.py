from collections import Counter

from utils.traffic import SOURCE, generate_traffic, load_seed_conversations, run_thread


def test_seed_mix():
    seeds = load_seed_conversations()
    assert Counter(s["category"] for s in seeds) == {"client_lookup": 12, "research": 7, "out_of_scope": 3, "client_lookup_by_id": 2}
    assert sum(len(s["turns"]) for s in seeds) == 33
    assert len({s["id"] for s in seeds}) == 24
    for seed in seeds:
        quotes_id = any("CL-" in turn for turn in seed["turns"])
        assert quotes_id == (seed["category"] == "client_lookup_by_id")


class RecordingAgent:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def invoke(self, payload, config):
        if self.fail:
            raise RuntimeError("boom")
        self.calls.append((payload, config))
        return {"messages": []}


def test_run_thread_tags_every_turn():
    seed = {"id": "s1", "category": "client_lookup", "turns": ["a", "b"]}
    agent = RecordingAgent()
    assert run_thread(agent, seed, "tid") == 2
    for turn, (payload, config) in enumerate(agent.calls, start=1):
        assert config["configurable"]["thread_id"] == "tid"
        assert config["metadata"] == {"source": SOURCE, "thread_id": "tid", "turn": turn, "seed_id": "s1", "category": "client_lookup"}
        assert payload["messages"][0]["content"] == seed["turns"][turn - 1]


def test_generate_traffic_counts_failures_without_raising(capsys):
    thread_ids = generate_traffic(threads=3, build_agent=lambda: RecordingAgent(fail=True))
    assert len(set(thread_ids)) == 3
    assert "failed: 3" in capsys.readouterr().out
