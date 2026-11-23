"""latest_insights_job and latest_red_team_run on fake HTTP responses."""

from types import SimpleNamespace

from utils.engine_reports import latest_insights_job, latest_red_team_run


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(self.status_code)


def fake_client(response):
    session = SimpleNamespace(get=lambda url, headers: response)
    return SimpleNamespace(api_url="https://api", session=session, _headers={})


def test_insights_job_returns_newest():
    jobs = [{"id": "a", "created_at": "2026-01-01"}, {"id": "b", "created_at": "2026-02-01"}]
    client = fake_client(FakeResponse(200, {"clustering_jobs": jobs}))
    assert latest_insights_job(client, "p")["id"] == "b"


def test_insights_job_is_none_without_jobs():
    assert latest_insights_job(fake_client(FakeResponse(200, {"clustering_jobs": []})), "p") is None


def test_insights_job_is_none_on_forbidden(capsys):
    assert latest_insights_job(fake_client(FakeResponse(403, {"detail": "no"})), "p") is None
    assert "403" in capsys.readouterr().out


def test_red_team_run_is_none_on_404():
    assert latest_red_team_run(fake_client(FakeResponse(404)), "p") is None
