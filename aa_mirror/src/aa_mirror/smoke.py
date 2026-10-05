"""Live smoke test: one request to the LLM endpoint, parse it, report schema drift. Stores nothing."""
from collections import Counter
from typing import Any

from .config import KEY_ENV, Settings
from .fetcher import ENDPOINTS, LLM_ENDPOINT, FetchError, fetch_json, make_client, parse_llms

EXPECTED_MODEL_KEYS = {
    "id", "name", "slug", "model_creator", "evaluations", "pricing",
    "median_output_tokens_per_second", "median_time_to_first_token_seconds",
    "median_time_to_first_answer_token",
}
EXPECTED_EVAL_KEYS = {
    "artificial_analysis_intelligence_index", "artificial_analysis_coding_index",
    "artificial_analysis_math_index",
}
EXPECTED_PRICING_KEYS = {"price_1m_blended_3_to_1", "price_1m_input_tokens", "price_1m_output_tokens"}


class MissingKey(RuntimeError):
    pass


def missing_key_message() -> str:
    return (
        f"{KEY_ENV} is not set. Put `{KEY_ENV}=<your key>` (no spaces, no quotes) in the .env "
        f"next to where you run the command, or in the systemd EnvironmentFile; see shelf-notes.md."
    )


def require_key(settings: Settings) -> str:
    key = settings.api_key()
    if not key:
        raise MissingKey(missing_key_message())
    return key


def schema_report(payload: Any) -> dict:
    data = [r for r in (payload or {}).get("data", []) if isinstance(r, dict)]
    top, evals, pricing = Counter(), Counter(), Counter()
    for r in data:
        top.update(r.keys())
        evals.update((r.get("evaluations") or {}).keys())
        pricing.update((r.get("pricing") or {}).keys())
    return {
        "missing_model_keys": sorted(EXPECTED_MODEL_KEYS - top.keys()),
        "new_model_keys": sorted(top.keys() - EXPECTED_MODEL_KEYS),
        "missing_eval_keys": sorted(EXPECTED_EVAL_KEYS - evals.keys()),
        "eval_keys_seen": sorted(evals),
        "missing_pricing_keys": sorted(EXPECTED_PRICING_KEYS - pricing.keys()),
    }


def run_smoke(settings: Settings, transport=None) -> dict:
    key = require_key(settings)
    ep = next(e for e in ENDPOINTS if e.key == LLM_ENDPOINT)
    with make_client(settings.base_url, key, settings.http_timeout, transport=transport) as client:
        status, raw, payload = fetch_json(client, ep)
    rows = parse_llms(payload)
    report = schema_report(payload)
    return {
        "endpoint": ep.path,
        "http_status": status,
        "bytes": len(raw),
        "models": len(rows),
        "with_intelligence_index": sum(r["intelligence_index"] is not None for r in rows),
        "with_blended_price": sum(r["price_blended"] is not None for r in rows),
        "with_output_speed": sum(r["output_tps"] is not None for r in rows),
        "unique_ids": len({r["model_id"] for r in rows}) == len(rows),
        **report,
        "ok": bool(rows) and not report["missing_model_keys"] and not report["missing_pricing_keys"],
    }
