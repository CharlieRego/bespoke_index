from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from aa_mirror import db
from aa_mirror.config import KEY_ENV
from aa_mirror.jobs import execute_run
from aa_mirror.web import create_app
from conftest import FAKE_KEY, FakeAA

HDR = {"X-Requested-With": "aa-mirror"}


@pytest.fixture
def fake():
    return FakeAA()


@pytest.fixture
def client(settings, fake, api_key):
    def runner(s, run_id):
        c = db.connect(s.db_path)
        try:
            execute_run(c, s, run_id, fake.factory)
        finally:
            c.close()
    return TestClient(create_app(settings, runner=runner))


def age_runs(settings, hours=1):
    c = db.connect(settings.db_path)
    c.execute("UPDATE runs SET started_at = ?", (db.iso(db.utcnow() - timedelta(hours=hours)),))
    c.close()


def test_empty_pages_render(client):
    for path in ["/", "/compare", "/runs", "/media/text-to-image"]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert "Source: <a href=\"https://artificialanalysis.ai/\"" in r.text
        assert r.headers["x-robots-tag"].startswith("noindex")


def test_refresh_requires_custom_header(client, fake):
    r = client.post("/api/refresh")
    assert r.status_code == 403
    assert fake.calls == []


def test_refresh_runs_job_then_cooldown(client, fake):
    r = client.post("/api/refresh", headers=HDR)
    assert r.status_code == 202 and r.json()["accepted"]
    assert len(fake.calls) == 6
    status = client.get("/api/status").json()
    assert status["last_run"]["status"] == "ok"
    assert status["last_refreshed_at"]
    assert status["cooldown_remaining_s"] > 0

    r = client.post("/api/refresh", headers=HDR)
    assert r.status_code == 429
    assert r.json()["reason"] == "cooldown" and "Retry-After" in r.headers
    assert len(fake.calls) == 6


def test_refresh_busy_returns_409(settings, api_key, fake):
    app = create_app(settings, runner=lambda s, run_id: None)
    c = TestClient(app)
    assert c.post("/api/refresh", headers=HDR).status_code == 202
    r = c.post("/api/refresh", headers=HDR)
    assert r.status_code == 409 and r.json()["reason"] == "busy"


def test_refresh_without_key_is_503_and_creates_no_run(settings, monkeypatch, fake):
    monkeypatch.delenv(KEY_ENV, raising=False)
    c = TestClient(create_app(settings, runner=lambda s, r: None))
    r = c.post("/api/refresh", headers=HDR)
    assert r.status_code == 503 and KEY_ENV in r.json()["message"]
    assert c.get("/api/status").json()["last_run"] is None


def test_pages_with_data_and_no_key_leak(client, settings):
    client.post("/api/refresh", headers=HDR)
    age_runs(settings)
    client.post("/api/refresh", headers=HDR)

    home = client.get("/")
    assert "Synthetic Alpha &lt;b&gt;" in home.text
    assert "\\u003cb\\u003e" in home.text
    assert "Synthetic Gamma" in home.text

    model = client.get("/model/00000000-0000-4000-8000-000000000001")
    assert model.status_code == 200 and "mmlu_pro" in model.text
    assert client.get("/model/does-not-exist").status_code == 404

    cmp = client.get("/compare")
    assert cmp.status_code == 200 and "unchanged" in cmp.text

    media = client.get("/media/text-to-image")
    assert "Synthetic Painter" in media.text
    assert client.get("/media/nope").status_code == 404

    for path in ["/", "/runs", "/api/status", "/compare", "/model/00000000-0000-4000-8000-000000000001"]:
        assert FAKE_KEY not in client.get(path).text


def test_no_api_docs_exposed(client):
    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 404
