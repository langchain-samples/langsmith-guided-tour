"""REST helpers for Insights reports and Red Teaming runs, which the SDK doesn't fully cover."""

from langsmith import Client


def latest_insights_job(client: Client, project_id: str) -> dict | None:
    """Return the newest Insights report job on a project, or None if there is none."""
    response = client.request_with_retries("GET", f"/sessions/{project_id}/insights")
    jobs = response.json()["clustering_jobs"]
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
