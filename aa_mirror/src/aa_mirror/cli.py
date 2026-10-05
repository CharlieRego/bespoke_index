import argparse
import json
import logging
import sys

from . import db
from .config import load_settings
from .fetcher import ENDPOINTS, FetchError
from .jobs import RefreshRejected, guard_state, refresh
from .queries import last_run
from .smoke import MissingKey, require_key, run_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aa-mirror")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("refresh", help="fetch one new snapshot (respects lock, cooldown and daily budget)")
    r.add_argument("--trigger", default="cli", choices=["cli", "timer", "manual"])
    r.add_argument("--dry-run", action="store_true", help="show what would be fetched and the guard state; no requests")
    sub.add_parser("smoke", help="live check: 1 request to the LLM endpoint, parse and report schema drift; stores nothing")
    sub.add_parser("status", help="show last run and guard state")
    s = sub.add_parser("serve", help="run the web UI")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = load_settings()

    if args.cmd in ("refresh", "smoke"):
        try:
            require_key(settings)
        except MissingKey as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if args.cmd == "smoke":
        try:
            report = run_smoke(settings)
        except FetchError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1

    if args.cmd == "refresh":
        if args.dry_run:
            conn = db.connect(settings.db_path)
            print(json.dumps({
                "db": str(settings.db_path),
                "endpoints": [settings.base_url + e.path for e in ENDPOINTS],
                **guard_state(conn, settings),
            }, indent=2))
            conn.close()
            return 0
        try:
            run_id, status = refresh(settings, args.trigger)
        except RefreshRejected as e:
            print(f"skipped ({e.reason}): {e}")
            return 0
        conn = db.connect(settings.db_path)
        print(f"run {run_id}: {status} - {last_run(conn)['message']}")
        conn.close()
        return 0 if status in ("ok", "partial") else 1

    if args.cmd == "status":
        conn = db.connect(settings.db_path)
        row = last_run(conn)
        print(json.dumps({"last_run": dict(row) if row else None, **guard_state(conn, settings)}, indent=2))
        conn.close()
        return 0

    import uvicorn
    from .web import create_app
    uvicorn.run(create_app(settings), host=args.host, port=args.port, proxy_headers=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
