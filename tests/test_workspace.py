from utils.workspace import ensure_model_config, ensure_workspace_secret


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, secrets=(), configs=()):
        self.secrets = list(secrets)
        self.configs = list(configs)
        self.calls = []

    def request_with_retries(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs.get("json")))
        if (method, path) == ("GET", "/workspaces/current/secrets"):
            return FakeResponse([{"key": key} for key in self.secrets])
        if (method, path) == ("GET", "/playground-settings"):
            return FakeResponse(self.configs)
        if (method, path) == ("POST", "/playground-settings"):
            return FakeResponse({"id": "cfg-1"})
        return FakeResponse({})


SPEC = {"model": "openai:gpt-5.6-luna", "base_url": "https://gateway.smith.langchain.com/openai", "use_responses_api": True}


def test_ensure_workspace_secret_creates_missing():
    client = FakeClient()
    assert ensure_workspace_secret(client, "GATEWAY_MODEL_API_KEY", "v") == "created"
    assert ("POST", "/workspaces/current/secrets", [{"key": "GATEWAY_MODEL_API_KEY", "value": "v"}]) in client.calls


def test_ensure_workspace_secret_keeps_existing():
    client = FakeClient(secrets=["GATEWAY_MODEL_API_KEY"])
    assert ensure_workspace_secret(client, "GATEWAY_MODEL_API_KEY", "v") == "already set"
    assert all(method == "GET" for method, _, _ in client.calls)


def test_ensure_model_config_creates_and_enables():
    client = FakeClient()
    assert ensure_model_config(client, "client-research-model", SPEC, "GATEWAY_MODEL_API_KEY") == "created"
    method, path, body = client.calls[1]
    assert (method, path) == ("POST", "/playground-settings")
    assert body["settings"] == {
        "modelId": "openai:gpt-5.6-luna",
        "envVarName": "GATEWAY_MODEL_API_KEY",
        "baseUrl": "https://gateway.smith.langchain.com/openai",
        "additional_kwargs": {"use_responses_api": True},
    }
    assert client.calls[2][:2] == ("PATCH", "/playground-settings/cfg-1")


def test_ensure_model_config_is_idempotent():
    client = FakeClient(configs=[{"id": "cfg-1", "name": "client-research-model"}])
    assert ensure_model_config(client, "client-research-model", SPEC, "GATEWAY_MODEL_API_KEY") == "already set"
    assert len(client.calls) == 1
