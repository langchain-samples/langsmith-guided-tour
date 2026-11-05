"""REST helpers for Insights reports and Red Teaming runs, which the SDK doesn't fully cover."""

from langsmith import Client
from langsmith.schemas import InsightsReport


def start_insights_report(client: Client, project_id: str, name: str, question: str) -> InsightsReport:
    """Start an Insights report over a project's last 7 days of root runs."""
    config = {
        "name": name,
        "user_context": {"What would you like to learn about your agent?": question},
        "last_n_hours": 7 * 24,
        # Insights calls OpenAI with the workspace secret OPENAI_API_KEY
        "model": "openai",
    }
    response = client.request_with_retries("POST", f"/sessions/{project_id}/insights", json=config)
    return InsightsReport(
        **response.json(),
        project_id=project_id,
        tenant_id=client._get_tenant_id(),
        host_url=client._host_url,
    )


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
