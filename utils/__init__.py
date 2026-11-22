"""Loads the repo-root .env on first `utils` import, so notebooks get it before any `Client()`."""

from pathlib import Path

from dotenv import load_dotenv

# Absolute path: notebooks run from modules/, scripts from the repo root.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
