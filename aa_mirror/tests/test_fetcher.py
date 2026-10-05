import json

import httpx
import pytest

from aa_mirror.fetcher import ENDPOINTS, FetchError, fetch_json, make_client, parse_llms, parse_media
from conftest import load_fixture


def test_parse_llms_maps_fields_and_uses_ids():
    rows = parse_llms(load_fixture("llms.json"))
    assert [r["model_id"] for r in rows] == [
        "00000000-0000-4000-8000-000000000001",
        "00000000-0000-4000-8000-000000000002",
        "00000000-0000-4000-8000-000000000003",
    ]
    a = rows[0]
    assert a["creator_id"] == "c0000000-0000-4000-8000-000000000001"
    assert a["creator_name"] == "Fixture Labs"
    assert a["intelligence_index"] == 61.5
    assert a["coding_index"] == 55.0
    assert a["math_index"] == 70.25
    assert (a["price_blended"], a["price_input"], a["price_output"]) == (3.5, 2.0, 8.0)
    assert (a["output_tps"], a["ttft_s"], a["ttfa_s"]) == (120.4, 0.45, 2.1)
    evals = json.loads(a["evaluations"])
    assert evals["mmlu_pro"] == 0.81 and evals["hle"] is None


def test_parse_llms_tolerates_nulls_zeros_and_missing_blocks():
    rows = {r["model_id"]: r for r in parse_llms(load_fixture("llms.json"))}
    b = rows["00000000-0000-4000-8000-000000000002"]
    assert b["intelligence_index"] is None
    assert b["price_blended"] == 0.0 and b["output_tps"] == 0.0
    assert json.loads(b["evaluations"])["mmlu_pro"] is None
    g = rows["00000000-0000-4000-8000-000000000003"]
    assert g["creator_name"] is None and g["price_blended"] is None and g["evaluations"] == "{}"


def test_parse_media():
    rows = parse_media(load_fixture("media.json"), "text-to-image")
    assert rows[0] == {
        "category": "text-to-image",
        "model_id": "m0000000-0000-4000-8000-000000000001",
        "name": "Synthetic Painter",
        "slug": "synthetic-painter",
        "creator_id": "c0000000-0000-4000-8000-000000000001",
        "creator_name": "Fixture Labs",
        "elo": 1101.7,
        "rank": 1,
        "ci95": "-5/+6",
        "appearances": 4321,
        "release_date": "2026-01-15",
    }
    assert rows[1]["slug"] is None and rows[1]["appearances"] is None


@pytest.mark.parametrize("payload", [None, [], {"status": 200}, {"data": "x"}])
def test_bad_shapes_raise(payload):
    with pytest.raises(FetchError):
        parse_llms(payload)


def _client(handler):
    return make_client("https://aa.test", "k", 5, transport=httpx.MockTransport(handler))


def test_fetch_sends_key_header():
    seen = {}

    def handler(req):
        seen["key"] = req.headers["x-api-key"]
        seen["path"] = req.url.path
        return httpx.Response(200, json={"data": []})

    with _client(handler) as c:
        status, raw, payload = fetch_json(c, ENDPOINTS[0])
    assert seen == {"key": "k", "path": "/api/v2/data/llms/models"}
    assert status == 200 and payload == {"data": []}


@pytest.mark.parametrize("code,fatal", [(401, True), (403, True), (429, True), (500, False)])
def test_fetch_http_errors(code, fatal):
    with _client(lambda req: httpx.Response(code, text="nope")) as c:
        with pytest.raises(FetchError) as ei:
            fetch_json(c, ENDPOINTS[0])
    assert ei.value.status == code and ei.value.fatal is fatal
    assert "k" not in str(ei.value).split()


def test_fetch_invalid_json():
    with _client(lambda req: httpx.Response(200, text="<html>")) as c:
        with pytest.raises(FetchError, match="invalid JSON"):
            fetch_json(c, ENDPOINTS[0])
