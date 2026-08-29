"""Centralized model initialization.

The notebooks all import `model` from here, so swapping providers
(OpenAI / Anthropic / Azure / Bedrock) only requires editing this file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
# Resolved from this file rather than the cwd, which isn't always modules/.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from langchain.chat_models import init_chat_model

# --- OpenAI via the LangSmith LLM Gateway (Module 3 §1.4) ---
# Routes every model call through the LangSmith Gateway.
# model = init_chat_model(
#     model="gpt-5.6-luna",
#     model_provider="openai",
#     base_url="https://gateway.smith.langchain.com/openai",
#     api_key=os.environ["LANGSMITH_API_KEY"],
#     reasoning_effort="none",
# )

# --- Default: OpenAI ---
model = init_chat_model("openai:gpt-5.6-luna", reasoning_effort="none")

# --- Anthropic ---
# model = init_chat_model("anthropic:claude-sonnet-4-6")

# --- Azure OpenAI ---
# from langchain_openai import AzureChatOpenAI
# model = AzureChatOpenAI(azure_deployment="gpt-4.1-mini", streaming=True)

# --- AWS Bedrock ---
# from langchain_aws import ChatBedrockConverse
# model = ChatBedrockConverse(
#     provider="anthropic",
#     model_id="anthropic.claude-sonnet-4-20250514-v1:0",
# )
