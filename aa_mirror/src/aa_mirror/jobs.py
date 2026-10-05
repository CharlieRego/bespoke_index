import logging
import sqlite3
import zlib
from datetime import datetime, timedelta
from typing import Callable

import httpx

from . import db
from .config import Settings
from .fetcher import (
    ENDPOINTS, LLM_COLUMNS, LLM_ENDPOINT, MEDIA_COLUMNS,
    FetchError, fetch_json, make_client, parse_llms, parse_media,
)
from .smoke import missing_key_message

log = logging.getLogger("aa_mirror")

ClientFactory = Callable[[Settings, str], httpx.Client]


class RefreshRejected(Exception):
    def __init__(self, reason: str, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.reason = reason
        self.retry_after = retry_after


def _requests_last_24h(conn: sqlite3.Connection, now: datetime) -> int:
    since = db.iso(now - timedelta(hours=24))
    row = conn.execute(
        "SELECT COALESCE(SUM(requests_made), 0) FROM runs WHERE started_at >= ?", (since,)
    ).fetchone()
    return int(row[0])


def guard_state(conn: sqlite3.Connection, settings: Settings, now: datetime | None = None) -> dict:
    now = now or db.utcnow()
    running = conn.execute(
        "SELECT id, started_at FROM runs WHERE status = 'running' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    last = conn.execute(
        "SELECT started_at FROM runs WHERE requests_made > 0 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    cooldown_left = 0
    if last:
        elapsed = (now - db.parse_iso(last["started_at"])).total_seconds()
        cooldown_left = max(0, int(settings.cooldown_seconds - elapsed))
    return {
        "running_run_id": running["id"] if running else None,
        "cooldown_remaining_s": cooldown_left,
        "requests_last_24h": _requests_last_24h(conn, now),
        "daily_request_budget": settings.daily_request_budget,
    }


def acquire_run(conn: sqlite3.Connection, settings: Settings, trigger: str, now: datetime | None = None) -> int:
    """Atomically claim the refresh lock. BEGIN IMMEDIATE serialises concurrent callers across processes."""
    now = now or db.utcnow()
    planned = len(ENDPOINTS)
    conn.execute("BEGIN IMMEDIATE")
    try:
        stale_before = db.iso(now - timedelta(seconds=settings.stale_lock_seconds))
        conn.execute(
            "UPDATE runs SET status = 'failed', finished_at = ?, message = 'abandoned (stale lock)' "
            "WHERE status = 'running' AND started_at < ?",
            (db.iso(now), stale_before),
        )
        state = guard_state(conn, settings, now)
        if state["running_run_id"] is not None:
            raise RefreshRejected("busy", f"refresh already running (run {state['running_run_id']})", 30)
        if state["cooldown_remaining_s"] > 0:
            s = state["cooldown_remaining_s"]
            raise RefreshRejected("cooldown", f"cooldown active, try again in {s}s", s)
        if state["requests_last_24h"] + planned > settings.daily_request_budget:
            raise RefreshRejected(
                "budget",
                f"daily request budget reached ({state['requests_last_24h']}/{settings.daily_request_budget} in last 24h)",
                3600,
            )
        cur = conn.execute(
            "INSERT INTO runs (trigger, status, started_at, requests_made) VALUES (?, 'running', ?, ?)",
            (trigger, db.iso(now), planned),
        )
        conn.execute("COMMIT")
        return int(cur.lastrowid)
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def _default_client(settings: Settings, api_key: str) -> httpx.Client:
    return make_client(settings.base_url, api_key, settings.http_timeout)


def _insert(conn: sqlite3.Connection, table: str, columns: tuple[str, ...], run_id: int, rows: list[dict]) -> None:
    cols = ("run_id",) + columns
    sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
    conn.executemany(sql, [(run_id,) + tuple(r[c] for c in columns) for r in rows])


def _finish(conn: sqlite3.Connection, run_id: int, status: str, requests: int, message: str) -> None:
    conn.execute(
        "UPDATE runs SET status = ?, finished_at = ?, requests_made = ?, message = ? WHERE id = ?",
        (status, db.iso(db.utcnow()), requests, message, run_id),
    )


def execute_run(conn: sqlite3.Connection, settings: Settings, run_id: int,
                client_factory: ClientFactory = _default_client) -> str:
    api_key = settings.api_key()
    if not api_key:
        _finish(conn, run_id, "failed", 0, missing_key_message())
        return "failed"

    requests, ok, errors, counts = 0, [], [], []
    try:
        with client_factory(settings, api_key) as client:
            for ep in ENDPOINTS:
                requests += 1
                try:
                    status, raw, payload = fetch_json(client, ep)
                    rows = parse_llms(payload) if ep.key == LLM_ENDPOINT else parse_media(payload, ep.key)
                except FetchError as e:
                    errors.append(str(e))
                    if e.fatal:
                        break
                    continue
                conn.execute("BEGIN IMMEDIATE")
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO payloads (run_id, endpoint, http_status, fetched_at, body) VALUES (?, ?, ?, ?, ?)",
                        (run_id, ep.key, status, db.iso(db.utcnow()), zlib.compress(raw)),
                    )
                    if ep.key == LLM_ENDPOINT:
                        _insert(conn, "llm_models", LLM_COLUMNS, run_id, rows)
                    else:
                        _insert(conn, "media_models", MEDIA_COLUMNS, run_id, rows)
                    conn.execute("COMMIT")
                except BaseException:
                    conn.execute("ROLLBACK")
                    raise
                ok.append(ep.key)
                counts.append(f"{ep.key}={len(rows)}")
    except Exception as e:
        errors.append(f"unexpected error: {type(e).__name__}")
        log.exception("refresh run %s crashed", run_id)

    if not ok:
        status = "failed"
    elif errors or len(ok) < len(ENDPOINTS):
        status = "partial"
    else:
        status = "ok"
    parts = []
    if counts:
        parts.append("rows: " + ", ".join(counts))
    if errors:
        parts.append("errors: " + "; ".join(errors))
    _finish(conn, run_id, status, requests, " | ".join(parts) or "no endpoints fetched")
    log.info("refresh run %s finished: %s (%s requests)", run_id, status, requests)
    return status


def refresh(settings: Settings, trigger: str, client_factory: ClientFactory = _default_client) -> tuple[int, str]:
    conn = db.connect(settings.db_path)
    try:
        run_id = acquire_run(conn, settings, trigger)
        return run_id, execute_run(conn, settings, run_id, client_factory)
    finally:
        conn.close()
