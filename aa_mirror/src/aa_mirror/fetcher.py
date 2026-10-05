import json
from dataclasses import dataclass
from typing import Any

import httpx

LLM_ENDPOINT = "llms"


@dataclass(frozen=True)
class Endpoint:
    key: str
    path: str


ENDPOINTS: tuple[Endpoint, ...] = (
    Endpoint(LLM_ENDPOINT, "/api/v2/data/llms/models"),
    Endpoint("text-to-image", "/api/v2/data/media/text-to-image"),
    Endpoint("image-editing", "/api/v2/data/media/image-editing"),
    Endpoint("text-to-speech", "/api/v2/data/media/text-to-speech"),
    Endpoint("text-to-video", "/api/v2/data/media/text-to-video"),
    Endpoint("image-to-video", "/api/v2/data/media/image-to-video"),
)
MEDIA_CATEGORIES = tuple(e.key for e in ENDPOINTS if e.key != LLM_ENDPOINT)

LLM_COLUMNS = (
    "model_id", "name", "slug", "creator_id", "creator_name", "release_date",
    "intelligence_index", "coding_index", "math_index",
    "price_blended", "price_input", "price_output",
    "output_tps", "ttft_s", "ttfa_s", "evaluations",
)
MEDIA_COLUMNS = (
    "category", "model_id", "name", "slug", "creator_id", "creator_name",
    "elo", "rank", "ci95", "appearances", "release_date",
)


class FetchError(Exception):
    def __init__(self, message: str, status: int | None = None, fatal: bool = False):
        super().__init__(message)
        self.status = status
        self.fatal = fatal


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> int | None:
    n = _num(v)
    return int(n) if n is not None else None


def _str(v: Any) -> str | None:
    return None if v is None else str(v)


def _rows(payload: Any) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise FetchError("unexpected payload shape (no data list)")
    return [r for r in payload["data"] if isinstance(r, dict) and r.get("id")]


def parse_llms(payload: Any) -> list[dict]:
    out = []
    for r in _rows(payload):
        creator = r.get("model_creator") or {}
        evals = r.get("evaluations") or {}
        pricing = r.get("pricing") or {}
        out.append({
            "model_id": str(r["id"]),
            "name": _str(r.get("name")),
            "slug": _str(r.get("slug")),
            "creator_id": _str(creator.get("id")),
            "creator_name": _str(creator.get("name")),
            "release_date": _str(r.get("release_date")),
            "intelligence_index": _num(evals.get("artificial_analysis_intelligence_index")),
            "coding_index": _num(evals.get("artificial_analysis_coding_index")),
            "math_index": _num(evals.get("artificial_analysis_math_index")),
            "price_blended": _num(pricing.get("price_1m_blended_3_to_1")),
            "price_input": _num(pricing.get("price_1m_input_tokens")),
            "price_output": _num(pricing.get("price_1m_output_tokens")),
            "output_tps": _num(r.get("median_output_tokens_per_second")),
            "ttft_s": _num(r.get("median_time_to_first_token_seconds")),
            "ttfa_s": _num(r.get("median_time_to_first_answer_token")),
            "evaluations": json.dumps(
                {k: _num(v) for k, v in evals.items() if not isinstance(v, (dict, list))},
                sort_keys=True,
            ),
        })
    return out


def parse_media(payload: Any, category: str) -> list[dict]:
    out = []
    for r in _rows(payload):
        creator = r.get("model_creator") or {}
        out.append({
            "category": category,
            "model_id": str(r["id"]),
            "name": _str(r.get("name")),
            "slug": _str(r.get("slug")),
            "creator_id": _str(creator.get("id")),
            "creator_name": _str(creator.get("name")),
            "elo": _num(r.get("elo")),
            "rank": _int(r.get("rank")),
            "ci95": _str(r.get("ci95")),
            "appearances": _int(r.get("appearances")),
            "release_date": _str(r.get("release_date")),
        })
    return out


def fetch_json(client: httpx.Client, endpoint: Endpoint) -> tuple[int, bytes, Any]:
    try:
        resp = client.get(endpoint.path)
    except httpx.HTTPError as e:
        raise FetchError(f"{endpoint.key}: network error ({type(e).__name__})") from None
    if resp.status_code == 401:
        raise FetchError(f"{endpoint.key}: HTTP 401 (check API key)", 401, fatal=True)
    if resp.status_code == 403:
        raise FetchError(f"{endpoint.key}: HTTP 403 (not available on this tier?)", 403)
    if resp.status_code == 429:
        raise FetchError(f"{endpoint.key}: HTTP 429 rate limited", 429, fatal=True)
    if resp.status_code != 200:
        raise FetchError(f"{endpoint.key}: HTTP {resp.status_code}", resp.status_code)
    try:
        return resp.status_code, resp.content, resp.json()
    except ValueError:
        raise FetchError(f"{endpoint.key}: invalid JSON", resp.status_code) from None


def make_client(base_url: str, api_key: str, timeout: float, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers={"x-api-key": api_key, "accept": "application/json"},
        timeout=timeout,
        transport=transport,
    )
