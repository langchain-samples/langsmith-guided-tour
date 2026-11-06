"""Research half of the client-research agent, hosted as a Managed Deep Agent."""

import os

from langchain_openai import ChatOpenAI
from managed_deepagents import define_deep_agent

from tools.search import web_search

# Same LLM Gateway model as utils/models.py; MDA builds copy only this folder.
model = ChatOpenAI(
    model="gpt-5.6-luna",
    base_url="https://gateway.smith.langchain.com/openai",
    use_responses_api=True,
    # The placeholder lets the deployment start before a key is set; runs then fail with an auth error.
    api_key=os.environ.get("LANGSMITH_GATEWAY_API_KEY", "missing-langsmith-gateway-api-key"),
)

agent = define_deep_agent(
    name="client-research-managed",
    model=model,
    tools=[web_search],
)
