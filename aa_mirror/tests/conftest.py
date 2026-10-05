import json
from pathlib import Path

import httpx
import pytest

from aa_mirror import db
from aa_mirror.config import KEY_ENV, Settings
from aa_mirror.fetcher import make_client

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_KEY = "test-key-not-real"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class FakeAA:
    """Mock transport serving synthetic fixtures; records request paths and the key header."""

    def __init__(self, overrides: dict[str, httpx.Response] | None = None):
        self.overrides = overrides or {}
        self.calls: list[str] = []
        self.keys: set[str] = set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request.url.path)
        self.keys.add(request.headers.get("x-api-key", ""))
        if request.url.path in self.overrides:
            return self.overrides[request.url.path]
        if request.url.path.endswith("/llms/models"):
            return httpx.Response(200, json=load_fixture("llms.json"))
        return httpx.Response(200, json=load_fixture("media.json"))

    def factory(self, settings: Settings, api_key: str) -> httpx.Client:
        return make_client(settings.base_url, api_key, 5, transport=httpx.MockTransport(self))


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path, base_url="https://aa.test", cooldown_seconds=900, daily_request_budget=20)


@pytest.fixture
def conn(settings):
    c = db.connect(settings.db_path)
    yield c
    c.close()


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setenv(KEY_ENV, FAKE_KEY)
    return FAKE_KEY
