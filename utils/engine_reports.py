"""REST helpers for Insights reports and Red Teaming runs, which the SDK doesn't fully cover."""

from langsmith import Client


def latest_insights_job(client: Client, project_id: str) -> dict | None:
    """Return the newest Insights report job on a project, or None if there is none or it can't be read."""
    url = f"{client.api_url}/sessions/{project_id}/insights"
    response = client.session.get(url, headers=client._headers)
    if not response.ok:
        # 403: no Insights entitlement or permission; 404: the project has no reports endpoint.
        print(f"Could not read Insights reports ({response.status_code}): check your plan and permissions.")
        return None
    jobs = response.json().get("clustering_jobs", [])
    if not jobs:
        return None
    return max(jobs, key=lambda job: job["created_at"])


def latest_red_team_run(client: Client, project_id: str) -> dict | None:
    """Return the newest Red Teaming run for an Engine environment, or None if none has run."""
    url = f"{client.api_url}/v1/platform/sessions/{project_id}/red-team-runs/latest"
    response = client.session.get(url, headers=client._headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()
