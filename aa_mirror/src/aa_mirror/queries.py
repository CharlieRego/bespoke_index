import json
import sqlite3


def recent_runs(conn: sqlite3.Connection, limit: int = 100) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def last_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()


def last_finished_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM runs WHERE status IN ('ok', 'partial', 'failed') ORDER BY id DESC LIMIT 1"
    ).fetchone()


def last_success(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM runs WHERE status IN ('ok', 'partial') ORDER BY id DESC LIMIT 1"
    ).fetchone()


def llm_snapshots(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT r.id, r.started_at, r.status, COUNT(m.model_id) AS n FROM runs r "
        "JOIN llm_models m ON m.run_id = r.id GROUP BY r.id ORDER BY r.id DESC"
    ).fetchall()


def latest_llm_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    snaps = llm_snapshots(conn)
    return snaps[0] if snaps else None


def llm_models(conn: sqlite3.Connection, run_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM llm_models WHERE run_id = ? ORDER BY intelligence_index IS NULL, intelligence_index DESC, name",
        (run_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def llm_model_history(conn: sqlite3.Connection, model_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT m.*, r.started_at FROM llm_models m JOIN runs r ON r.id = m.run_id "
        "WHERE m.model_id = ? ORDER BY r.id",
        (model_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["evaluations"] = json.loads(d["evaluations"] or "{}")
        out.append(d)
    return out


def media_snapshot(conn: sqlite3.Connection, category: str) -> tuple[sqlite3.Row | None, list[dict]]:
    run = conn.execute(
        "SELECT r.* FROM runs r WHERE EXISTS (SELECT 1 FROM media_models m WHERE m.run_id = r.id AND m.category = ?) "
        "ORDER BY r.id DESC LIMIT 1",
        (category,),
    ).fetchone()
    if not run:
        return None, []
    rows = conn.execute(
        "SELECT * FROM media_models WHERE run_id = ? AND category = ? ORDER BY rank IS NULL, rank, elo DESC",
        (run["id"], category),
    ).fetchall()
    return run, [dict(r) for r in rows]


COMPARE_FIELDS = ("intelligence_index", "coding_index", "math_index", "price_blended", "output_tps", "ttft_s")


def compare_snapshots(conn: sqlite3.Connection, run_a: int, run_b: int) -> dict:
    a = {m["model_id"]: m for m in llm_models(conn, run_a)}
    b = {m["model_id"]: m for m in llm_models(conn, run_b)}
    changed = []
    for mid in a.keys() & b.keys():
        deltas = {}
        for f in COMPARE_FIELDS:
            va, vb = a[mid][f], b[mid][f]
            if va != vb:
                deltas[f] = (va, vb, (vb - va) if va is not None and vb is not None else None)
        if deltas:
            changed.append({"model_id": mid, "name": b[mid]["name"], "creator_name": b[mid]["creator_name"], "deltas": deltas})
    changed.sort(key=lambda c: -abs((c["deltas"].get("intelligence_index") or (0, 0, 0))[2] or 0))
    return {
        "added": sorted((b[m] for m in b.keys() - a.keys()), key=lambda m: m["name"] or ""),
        "removed": sorted((a[m] for m in a.keys() - b.keys()), key=lambda m: m["name"] or ""),
        "changed": changed,
        "unchanged": len(a.keys() & b.keys()) - len(changed),
    }
