import threading
import zlib
from datetime import timedelta

import httpx
import pytest

from aa_mirror import db
from aa_mirror.config import KEY_ENV
from aa_mirror.fetcher import ENDPOINTS
from aa_mirror.jobs import RefreshRejected, acquire_run, execute_run, guard_state, refresh
from conftest import FAKE_KEY, FakeAA


def test_acquire_creates_running_run_with_reserved_requests(conn, settings):
    run_id = acquire_run(conn, settings, "manual")
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert row["status"] == "running" and row["trigger"] == "manual"
    assert row["requests_made"] == len(ENDPOINTS)


def test_second_acquire_is_busy_while_running(conn, settings):
    acquire_run(conn, settings, "manual")
    with pytest.raises(RefreshRejected) as ei:
        acquire_run(conn, settings, "timer")
    assert ei.value.reason == "busy"


def test_stale_running_lock_is_released(conn, settings):
    now = db.utcnow()
    first = acquire_run(conn, settings, "manual", now=now - timedelta(hours=2))
    conn.execute("UPDATE runs SET requests_made = 0 WHERE id = ?", (first,))
    second = acquire_run(conn, settings, "manual", now=now)
    assert second != first
    row = conn.execute("SELECT status, message FROM runs WHERE id = ?", (first,)).fetchone()
    assert row["status"] == "failed" and "stale" in row["message"]


def test_cooldown_blocks_then_expires(conn, settings):
    now = db.utcnow()
    run_id = acquire_run(conn, settings, "manual", now=now)
    conn.execute("UPDATE runs SET status = 'ok' WHERE id = ?", (run_id,))
    with pytest.raises(RefreshRejected) as ei:
        acquire_run(conn, settings, "manual", now=now + timedelta(seconds=60))
    assert ei.value.reason == "cooldown"
    assert 0 < ei.value.retry_after <= settings.cooldown_seconds
    acquire_run(conn, settings, "manual", now=now + timedelta(seconds=settings.cooldown_seconds + 1))


def test_cooldown_ignores_runs_that_made_no_requests(conn, settings):
    now = db.utcnow()
    run_id = acquire_run(conn, settings, "manual", now=now)
    conn.execute("UPDATE runs SET status = 'failed', requests_made = 0 WHERE id = ?", (run_id,))
    acquire_run(conn, settings, "manual", now=now + timedelta(seconds=5))


def test_daily_budget(conn, settings):
    now = db.utcnow() - timedelta(hours=20)
    for i in range(3):
        t = now + timedelta(hours=i * 2)
        rid = acquire_run(conn, settings, "timer", now=t)
        conn.execute("UPDATE runs SET status = 'ok' WHERE id = ?", (rid,))
    # 3 runs x 6 requests = 18 of a 20 budget: the next 6 would exceed it
    with pytest.raises(RefreshRejected) as ei:
        acquire_run(conn, settings, "manual", now=db.utcnow())
    assert ei.value.reason == "budget"
    # requests older than 24h roll off
    acquire_run(conn, settings, "manual", now=db.utcnow() + timedelta(hours=5))


def test_concurrent_acquire_only_one_wins(settings):
    db.connect(settings.db_path).close()
    results, barrier = [], threading.Barrier(8)

    def worker():
        c = db.connect(settings.db_path)
        barrier.wait()
        try:
            results.append(acquire_run(c, settings, "manual"))
        except RefreshRejected as e:
            results.append(e.reason)
        finally:
            c.close()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(isinstance(r, int) for r in results) == 1
    assert all(r in ("busy", "cooldown") for r in results if not isinstance(r, int))


def test_execute_run_stores_snapshot(conn, settings, api_key):
    fake = FakeAA()
    run_id = acquire_run(conn, settings, "cli")
    assert execute_run(conn, settings, run_id, fake.factory) == "ok"
    assert fake.keys == {FAKE_KEY}
    assert len(fake.calls) == len(ENDPOINTS)
    run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert run["status"] == "ok" and run["requests_made"] == len(ENDPOINTS) and run["finished_at"]
    assert FAKE_KEY not in run["message"]
    assert conn.execute("SELECT COUNT(*) FROM llm_models WHERE run_id = ?", (run_id,)).fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(DISTINCT category) FROM media_models").fetchone()[0] == len(ENDPOINTS) - 1
    body = conn.execute("SELECT body FROM payloads WHERE endpoint = 'llms'").fetchone()[0]
    assert b"Synthetic Alpha" in zlib.decompress(body)


def test_execute_run_partial_on_endpoint_error(conn, settings, api_key):
    fake = FakeAA({"/api/v2/data/media/text-to-video": httpx.Response(500)})
    run_id = acquire_run(conn, settings, "cli")
    assert execute_run(conn, settings, run_id, fake.factory) == "partial"
    msg = conn.execute("SELECT message FROM runs WHERE id = ?", (run_id,)).fetchone()[0]
    assert "text-to-video: HTTP 500" in msg


def test_execute_run_stops_on_auth_error(conn, settings, api_key):
    fake = FakeAA({"/api/v2/data/llms/models": httpx.Response(401)})
    run_id = acquire_run(conn, settings, "cli")
    assert execute_run(conn, settings, run_id, fake.factory) == "failed"
    assert len(fake.calls) == 1
    run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert run["requests_made"] == 1 and "check API key" in run["message"]


def test_execute_run_without_key_fails_clearly(conn, settings, monkeypatch):
    monkeypatch.delenv(KEY_ENV, raising=False)
    fake = FakeAA()
    run_id = acquire_run(conn, settings, "cli")
    assert execute_run(conn, settings, run_id, fake.factory) == "failed"
    run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert KEY_ENV in run["message"] and run["requests_made"] == 0
    assert fake.calls == []
    assert guard_state(conn, settings)["cooldown_remaining_s"] == 0


def test_refresh_end_to_end_and_history_accumulates(settings, api_key):
    fake = FakeAA()
    r1, s1 = refresh(settings, "timer", fake.factory)
    with pytest.raises(RefreshRejected):
        refresh(settings, "manual", fake.factory)
    c = db.connect(settings.db_path)
    c.execute("UPDATE runs SET started_at = ? WHERE id = ?", (db.iso(db.utcnow() - timedelta(hours=1)), r1))
    c.close()
    r2, s2 = refresh(settings, "manual", fake.factory)
    assert (s1, s2) == ("ok", "ok") and r2 > r1
    c = db.connect(settings.db_path)
    assert c.execute("SELECT COUNT(DISTINCT run_id) FROM llm_models").fetchone()[0] == 2
    c.close()
