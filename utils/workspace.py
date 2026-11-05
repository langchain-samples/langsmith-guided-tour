"""Workspace setup over REST: no public SDK method stores secrets or model configurations."""

from typing import Literal

from langsmith.utils import raise_for_status_with_text

EnsureStatus = Literal["created", "already set"]

MODEL_CONFIG_AVAILABILITY = {
    "available_in_playground": True,
    "available_in_evaluators": True,
    "available_in_polly": True,
    "available_in_insights_heavy": True,
    "available_in_insights_light": True,
}


def ensure_workspace_secret(client, key: str, value: str) -> EnsureStatus:
    """Store `key` as a workspace secret unless it exists; never overwrites or echoes the value."""
    response = client.request_with_retries("GET", "/workspaces/current/secrets")
    raise_for_status_with_text(response)
    existing_keys = {secret.get("key") for secret in response.json()}
    if key in existing_keys:
        return "already set"

    response = client.request_with_retries("POST", "/workspaces/current/secrets", json=[{"key": key, "value": value}])
    raise_for_status_with_text(response)
    return "created"


def ensure_model_config(client, name: str, model_spec: dict, secret_name: str) -> EnsureStatus:
    """Add a workspace model configuration for `model_spec`, keyed by the secret `secret_name`."""
    response = client.request_with_retries("GET", "/playground-settings")
    raise_for_status_with_text(response)
    if any(config.get("name") == name for config in response.json()):
        return "already set"

    settings = {"modelId": model_spec["model"], "envVarName": secret_name}
    if "base_url" in model_spec:
        settings["baseUrl"] = model_spec["base_url"]
    settings["additional_kwargs"] = {k: v for k, v in model_spec.items() if k not in ("model", "base_url")}
    body = {"name": name, "settings": settings, "settings_type": "simple", "scope": "workspace"}
    response = client.request_with_retries("POST", "/playground-settings", json=body)
    raise_for_status_with_text(response)
    config_id = response.json()["id"]

    # Not every availability flag defaults on; set them all explicitly.
    response = client.request_with_retries("PATCH", f"/playground-settings/{config_id}", json=MODEL_CONFIG_AVAILABILITY)
    raise_for_status_with_text(response)
    return "created"
