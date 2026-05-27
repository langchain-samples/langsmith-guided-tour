"""Shared LLM-as-judge output schemas for online evaluators.

Each schema is a JSON Schema dict accepted by `create_run_rule` / the LangSmith
online-evaluator API.  Centralising here lets the SDK rule registration and the
notebook stay in sync with whatever the UI shows.
"""

# JSON Schema for the client-research correctness evaluator.
# Matches the online evaluator registered in modules/04_online_evals.ipynb.
correctness_schema: dict = {
    "title": "correctness",
    "description": (
        "Score whether the client research response is grounded, sourced, "
        "and honest about unknown clients."
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
