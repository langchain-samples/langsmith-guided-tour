"""Research-associate agent used as the agent-under-test for the Harbor environment eval.

Harbor's `--agent langgraph` loads the `deep_agent` graph declared in
`langgraph.json` and calls `make_graph(config)` once per trial.

The model is built here rather than from `config["configurable"]["model"]` (the
usual Harbor convention) -- this container can't import `utils/models.py`. It
routes through the LangSmith Gateway, so only `LANGSMITH_API_KEY` is needed and
Harbor forwards it automatically. Note this differs from `utils/models.py`,
which defaults to OpenAI direct: Part B needs Gateway access on the workspace.

`root_dir` is pinned to `/app` rather than `.` -- Harbor's langgraph runner
doesn't necessarily execute from the container's working directory, so a
relative root would resolve against a cwd this agent doesn't control.

`virtual_mode=False`, deliberately: with virtual_mode=True, an absolute path
like "/app/analysis.py" is treated as *virtual* and gets re-rooted under
root_dir, landing at the real "/app/app/analysis.py" -- a real double-prefix
bug we hit in testing, since the agent's `execute` tool shows it a real `pwd`
of `/app` and it naturally reuses that prefix with write_file/read_file too.
virtual_mode=False makes absolute paths literal (matching what `execute`
sees) and still resolves bare relative paths under root_dir either way.

Requirements (what to read, what to write, the reproducibility rule) live in
`instruction.md`, not here -- the system prompt only sets the agent's role
and the one path convention that matters for this backend.
"""

import os

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langchain.chat_models import init_chat_model

SYSTEM_PROMPT = (
    "You are a research associate. Read the source files before answering. "
    "Use plain relative file paths (e.g. `analysis.py`, `report/take.md`) -- "
    "not absolute paths -- for every file you read or write."
)


def make_graph(config):
    model = init_chat_model(
        model="gpt-5.6-luna",
        model_provider="openai",
        base_url="https://gateway.smith.langchain.com/openai",
        api_key=os.environ["LANGSMITH_API_KEY"],
        # Reasoning model; /v1/chat/completions rejects function tools unless
        # reasoning_effort is off, and this agent always binds tools.
        reasoning_effort="none",
    )
    return create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        backend=LocalShellBackend(root_dir="/app", virtual_mode=False),
    )
