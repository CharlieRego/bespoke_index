import json
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import APP_NAME, db, queries
from .config import Settings, load_settings
from .fetcher import MEDIA_CATEGORIES
from .jobs import RefreshRejected, acquire_run, execute_run, guard_state
from .smoke import missing_key_message

HERE = Path(__file__).parent
Runner = Callable[[Settings, int], None]


def _thread_runner(settings: Settings, run_id: int) -> None:
    def work():
        conn = db.connect(settings.db_path)
        try:
            execute_run(conn, settings, run_id)
        finally:
            conn.close()
    threading.Thread(target=work, name=f"aa-refresh-{run_id}", daemon=True).start()


def script_json(obj) -> str:
    return json.dumps(obj).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def fmt(v, digits: int = 1) -> str:
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:,.{digits}f}"
    return str(v)


def create_app(settings: Settings | None = None, runner: Runner | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title=APP_NAME, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.runner = runner or _thread_runner
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["fmt"] = fmt
    templates.env.globals.update(app_name=APP_NAME, media_categories=MEDIA_CATEGORIES)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    @contextmanager
    def conn():
        c = db.connect(settings.db_path)
        try:
            yield c
        finally:
            c.close()

    @app.middleware("http")
    async def private_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Frame-Options"] = "DENY"
        return resp

    def status_payload(c) -> dict:
        last = queries.last_run(c)
        finished = queries.last_finished_run(c)
        success = queries.last_success(c)
        return {
            "last_run": dict(last) if last else None,
            "last_finished_run": dict(finished) if finished else None,
            "last_refreshed_at": success["finished_at"] if success else None,
            **guard_state(c, settings),
        }

    def render(request: Request, name: str, ctx: dict):
        with conn() as c:
            ctx.setdefault("status", status_payload(c))
        return templates.TemplateResponse(request, name, ctx)

    @app.get("/robots.txt", include_in_schema=False)
    def robots():
        return PlainTextResponse("User-agent: *\nDisallow: /\n")

    @app.get("/")
    def leaderboard(request: Request, run: int | None = None):
        with conn() as c:
            snaps = queries.llm_snapshots(c)
            snap = next((s for s in snaps if s["id"] == run), None) if run else (snaps[0] if snaps else None)
            models = queries.llm_models(c, snap["id"]) if snap else []
        chart = [
            {k: m[k] for k in ("model_id", "name", "creator_name", "intelligence_index", "price_blended", "output_tps", "ttft_s")}
            for m in models
        ]
        creators = sorted({m["creator_name"] for m in models if m["creator_name"]})
        return render(request, "leaderboard.html", {
            "snap": snap, "snaps": snaps, "models": models, "creators": creators,
            "chart_json": script_json(chart),
        })

    @app.get("/model/{model_id}")
    def model_detail(request: Request, model_id: str):
        with conn() as c:
            history = queries.llm_model_history(c, model_id)
        if not history:
            raise HTTPException(404, "model not found in any snapshot")
        latest = history[-1]
        series = [
            {k: h[k] for k in ("started_at", "intelligence_index", "price_blended", "output_tps", "ttft_s")}
            for h in history
        ]
        return render(request, "model.html", {
            "m": latest, "history": history, "series_json": script_json(series),
        })

    @app.get("/compare")
    def compare(request: Request, a: int | None = None, b: int | None = None):
        with conn() as c:
            snaps = queries.llm_snapshots(c)
            ids = [s["id"] for s in snaps]
            if b is None and ids:
                b = ids[0]
            if a is None and len(ids) > 1:
                a = ids[1]
            result = queries.compare_snapshots(c, a, b) if a in ids and b in ids else None
        by_id = {s["id"]: s for s in snaps}
        return render(request, "compare.html", {
            "snaps": snaps, "a": a, "b": b, "snap_a": by_id.get(a), "snap_b": by_id.get(b), "result": result,
        })

    @app.get("/media/{category}")
    def media(request: Request, category: str):
        if category not in MEDIA_CATEGORIES:
            raise HTTPException(404)
        with conn() as c:
            run, rows = queries.media_snapshot(c, category)
        return render(request, "media.html", {"category": category, "run": run, "rows": rows})

    @app.get("/runs")
    def runs(request: Request):
        with conn() as c:
            rows = queries.recent_runs(c)
        return render(request, "runs.html", {"runs": rows})

    @app.get("/api/status")
    def api_status():
        with conn() as c:
            return status_payload(c)

    @app.post("/api/refresh")
    def api_refresh(request: Request):
        if request.headers.get("x-requested-with") != "aa-mirror":
            raise HTTPException(403, "missing X-Requested-With header")
        if not settings.api_key():
            return JSONResponse({"accepted": False, "reason": "no_key", "message": missing_key_message()}, 503)
        with conn() as c:
            try:
                run_id = acquire_run(c, settings, "manual")
            except RefreshRejected as e:
                code = 409 if e.reason == "busy" else 429
                headers = {"Retry-After": str(e.retry_after)} if e.retry_after else None
                return JSONResponse({"accepted": False, "reason": e.reason, "message": str(e)}, code, headers)
        app.state.runner(settings, run_id)
        return JSONResponse({"accepted": True, "run_id": run_id}, 202)

    return app
