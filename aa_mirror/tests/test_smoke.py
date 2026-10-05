import httpx
import pytest

from aa_mirror import cli
from aa_mirror.config import KEY_ENV
from aa_mirror.smoke import MissingKey, require_key, run_smoke, schema_report
from conftest import FAKE_KEY, FakeAA, load_fixture


def test_smoke_against_fixture(settings, api_key):
    fake = FakeAA()
    report = run_smoke(settings, transport=httpx.MockTransport(fake))
    assert fake.calls == ["/api/v2/data/llms/models"]
    assert report["models"] == 3 and report["with_intelligence_index"] == 1
    assert report["unique_ids"] and report["ok"]
    assert FAKE_KEY not in str(report)


def test_schema_report_flags_drift():
    payload = load_fixture("llms.json")
    for r in payload["data"]:
        r.pop("pricing", None)
        r["brand_new_field"] = 1
    rep = schema_report(payload)
    assert "pricing" in rep["missing_model_keys"]
    assert "brand_new_field" in rep["new_model_keys"]


def test_require_key_message(settings, monkeypatch):
    monkeypatch.delenv(KEY_ENV, raising=False)
    with pytest.raises(MissingKey, match=KEY_ENV):
        require_key(settings)


@pytest.mark.parametrize("cmd", [["smoke"], ["refresh"]])
def test_cli_missing_key_exits_2(cmd, monkeypatch, tmp_path, capsys):
    monkeypatch.delenv(KEY_ENV, raising=False)
    monkeypatch.setenv("AA_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert cli.main(cmd) == 2
    assert KEY_ENV in capsys.readouterr().err
