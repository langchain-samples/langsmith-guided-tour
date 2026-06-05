"""Shared LLM-as-judge output schemas for online evaluators.

Each schema is a JSON Schema dict accepted by `create_run_rule` / the LangSmith
online-evaluator API.  Centralising here lets the SDK rule registration and the
notebook stay in sync with whatever the UI shows.
"""

# JSON Schema for the retail-assistant correctness evaluator.
# Matches the online evaluator registered in modules/05_online_evals.ipynb.
correctness_schema: dict = {
    "title": "correctness",
    "description": (
        "Score whether the retail assistant response is grounded in tool "
        "results, honest about unknown products/orders/accounts, and escalates "
        "out-of-scope issues."
    ),
    "type": "object",
    "properties": {
        "correctness": {
            "type": "boolean",
            "description": "True if all three criteria are met",
        },
        "comment": {
            "type": "string",
            "description": "One short sentence explaining the score",
        },
    },
    "required": ["correctness", "comment"],
    "strict": True,
}
