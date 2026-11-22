"""Loads the repo-root .env on first `utils` import, so notebooks get it before any `Client()`."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Absolute path: notebooks run from modules/, scripts from the repo root.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
# Without this, traces from a .env missing LANGSMITH_PROJECT land in a project named "default".
os.environ.setdefault("LANGSMITH_PROJECT", "langsmith-poc")
