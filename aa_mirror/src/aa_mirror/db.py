import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    requests_made INTEGER NOT NULL DEFAULT 0,
    message TEXT
);
CREATE INDEX IF NOT EXISTS runs_started ON runs(started_at);

CREATE TABLE IF NOT EXISTS payloads (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    endpoint TEXT NOT NULL,
    http_status INTEGER,
    fetched_at TEXT NOT NULL,
    body BLOB,
    PRIMARY KEY (run_id, endpoint)
);

CREATE TABLE IF NOT EXISTS llm_models (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    model_id TEXT NOT NULL,
    name TEXT,
    slug TEXT,
    creator_id TEXT,
    creator_name TEXT,
    release_date TEXT,
    intelligence_index REAL,
    coding_index REAL,
    math_index REAL,
    price_blended REAL,
    price_input REAL,
    price_output REAL,
    output_tps REAL,
    ttft_s REAL,
    ttfa_s REAL,
    evaluations TEXT,
    PRIMARY KEY (run_id, model_id)
);
CREATE INDEX IF NOT EXISTS llm_models_model ON llm_models(model_id);

CREATE TABLE IF NOT EXISTS media_models (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    category TEXT NOT NULL,
    model_id TEXT NOT NULL,
    name TEXT,
    slug TEXT,
    creator_id TEXT,
    creator_name TEXT,
    elo REAL,
    rank INTEGER,
    ci95 TEXT,
    appearances INTEGER,
    release_date TEXT,
    PRIMARY KEY (run_id, category, model_id)
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn
