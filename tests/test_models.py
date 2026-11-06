import pytest

from utils import models


def test_default_pair_routes_through_gateway():
    assert models.MODEL_SPEC["model"] == "openai:gpt-5.6-luna"
    assert models.MODEL_SPEC["base_url"] == "https://gateway.smith.langchain.com/openai"
    assert models.API_KEY_ENV == "LANGSMITH_GATEWAY_API_KEY"
    assert models.MODEL_ID == "openai:gpt-5.6-luna"


def test_make_model_applies_overrides():
    model = models.make_model(max_retries=1)
    assert model.openai_api_base == "https://gateway.smith.langchain.com/openai"
    assert model.max_retries == 1  # gpt-5 models drop temperature


def test_make_model_names_missing_key(monkeypatch):
    monkeypatch.delenv("LANGSMITH_GATEWAY_API_KEY")
    with pytest.raises(RuntimeError, match="LANGSMITH_GATEWAY_API_KEY"):
        models.make_model()
