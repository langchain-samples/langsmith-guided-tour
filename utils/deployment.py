"""Deploy helpers for Module 7: deployment env files and Agent Server lookups."""

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, set_key
from langgraph_cli.host_backend import ControlPlaneEndpoints, HostBackendClient
from langsmith import Client


@dataclass(frozen=True)
class Deployment:
    id: str
    name: str
    api_url: str
    workspace_id: str


def write_env_subset(
    source: Path,
    target: Path,
    keys: Iterable[str],
    overrides: Mapping[str, str] | None = None,
) -> list[str]:
    """Write only the named entries of `source` (plus `overrides`) to `target`; return the names written."""
    values = dotenv_values(source)
    entries = {key: values[key] for key in keys if values.get(key)}
    entries.update(overrides or {})
    target.write_text("")
    for key, value in entries.items():
        set_key(str(target), key, value)
    return list(entries)


def _host_backend_client() -> HostBackendClient:
    endpoints = ControlPlaneEndpoints.resolve(None, os.getenv("LANGSMITH_ENDPOINT"))
    return HostBackendClient(
        endpoints.control_plane_url,
        os.environ["LANGSMITH_API_KEY"],
        tenant_id=os.getenv("LANGSMITH_WORKSPACE_ID") or None,
    )


def find_deployment(
    *,
    name: str | None = None,
    agent_id: str | None = None,
    environment: str | None = None,
    client: HostBackendClient | None = None,
) -> Deployment:
    """Return the one live, non-preview deployment matching the filters."""
    client = client or _host_backend_client()
    found = client.list_deployments(name=name, agent_id=agent_id, agent_environment=environment)
    matches = [
        deployment
        for deployment in found
        if not deployment.get("is_preview") and (name is None or deployment.get("name") == name)
    ]
    if len(matches) != 1:
        raise LookupError(f"Expected one deployment, found {len(matches)}. Did the deploy cell finish?")
    deployment = matches[0]
    api_url = (deployment.get("source_config") or {}).get("custom_url")
    if not api_url:
        raise LookupError(f"Deployment {deployment['id']} has no API URL yet; wait until it is DEPLOYED.")
    return Deployment(
        id=str(deployment["id"]),
        name=str(deployment["name"]),
        api_url=api_url,
        workspace_id=str(deployment.get("tenant_id", "")),
    )


def context_hub_url(client: Client, repo_handle: str, workspace_id: str) -> str:
    """Return the LangSmith UI link to a Context Hub agent repo."""
    # Same path as the Context Hub link on a deployment's Details card.
    return f"{client._host_url}/context/{repo_handle}?organizationId={workspace_id}"


def reply_text(state: Mapping[str, Any]) -> str:
    """Return the text of the last message in an Agent Server run result."""
    content = state["messages"][-1]["content"]
    if isinstance(content, str):
        return content
    return "".join(block.get("text", "") for block in content if block.get("type") == "text")
