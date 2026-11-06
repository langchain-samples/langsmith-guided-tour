"""Model setup for every module and agent. Pick exactly one MODEL_SPEC / API_KEY_ENV pair below."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

# --- OpenAI gpt-5.6-luna via the LangSmith LLM Gateway (default) ---
MODEL_SPEC = {
    "model": "openai:gpt-5.6-luna",
    "base_url": "https://gateway.smith.langchain.com/openai",
    "use_responses_api": True,
}
# The gateway key may come from another workspace that has model access.
API_KEY_ENV = "LANGSMITH_GATEWAY_API_KEY"

# --- Anthropic via the LangSmith LLM Gateway ---
# MODEL_SPEC = {"model": "anthropic:claude-sonnet-4-6", "base_url": "https://gateway.smith.langchain.com/anthropic"}
# API_KEY_ENV = "LANGSMITH_GATEWAY_API_KEY"

# --- Anthropic, direct ---
# MODEL_SPEC = {"model": "anthropic:claude-sonnet-4-6"}
# API_KEY_ENV = "ANTHROPIC_API_KEY"

# --- OpenAI, direct ---
# MODEL_SPEC = {"model": "openai:gpt-5.6-luna", "use_responses_api": True}
# API_KEY_ENV = "OPENAI_API_KEY"

# --- Azure OpenAI ---
# MODEL_SPEC = {"model": "azure_openai:gpt-5.6-terra", "azure_deployment": "gpt-5.6-terra"}
# API_KEY_ENV = "AZURE_OPENAI_API_KEY"

# --- AWS Bedrock ---
# MODEL_SPEC = {"model": "bedrock_converse:anthropic.claude-sonnet-4-20250514-v1:0"}
# API_KEY_ENV = None  # Bedrock uses the AWS credential chain, so make_model passes no api_key.

MODEL_ID = MODEL_SPEC["model"]


def make_model(**overrides):
    """Build the chat model from MODEL_SPEC; keyword overrides win (e.g. max_retries=1)."""
    kwargs = {**MODEL_SPEC, **overrides}
    if API_KEY_ENV is None:
        return init_chat_model(**kwargs)
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"Set {API_KEY_ENV} in .env (see utils/models.py for the model in use).")
    return init_chat_model(**kwargs, api_key=api_key)
