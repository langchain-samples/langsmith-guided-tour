"""Tests run on dummy keys with tracing off, never on the real .env."""

import os

import dotenv

dotenv.load_dotenv = lambda *args, **kwargs: False  # utils/* import load_dotenv after this runs
for name in ("LANGSMITH_GATEWAY_API_KEY", "TAVILY_API_KEY", "LANGSMITH_API_KEY"):
    os.environ[name] = "test-key"
os.environ["LANGSMITH_TRACING"] = "false"
for name in ("LANGSMITH_PROJECT", "LANGSMITH_AGENT_ID", "LANGSMITH_AGENT_ENVIRONMENT"):
    os.environ.pop(name, None)
