# CLAUDE.md

Single source of truth for all AI coding agents working in this repo (Claude Code, Codex, Cursor, etc.). `AGENTS.md` points here — **maintain this file, not `AGENTS.md`.**

## Project

`bespoke_index` — Bespoke AI Model Indices. Part of a data science portfolio.
Early-stage; update this file as structure emerges.

## Layout

- `aa_mirror/` — AA Study Mirror (private): fetcher + FastAPI UI over the Artificial Analysis free Data API. Own `pyproject.toml`/`uv.lock`. Code in `src/aa_mirror/`, tests in `tests/` (synthetic fixtures only), systemd/Caddy files in `deploy/`.
  - Snapshots go to SQLite at `$AA_DATA_DIR/aa_mirror.sqlite3` (default `aa_mirror/data/`, gitignored; `/var/lib/aa-mirror` on the VPS).
  - Internal-only: bind to localhost, reach via SSH tunnel or Caddy basic_auth. No public deploy, exports or raw-payload endpoints.
  - All fetches go through `jobs.acquire_run` (SQLite lock + cooldown + 24h request budget); don't add code paths that call the API around it.

## Architecture

- Frontpage: Vercel, on the apex domain, pointing at an API.
- API: hosted on an Onidel Sydney VPS at `api.<domain>` (Caddy auto-TLS, systemd).
- The VPS doubles as the dev environment. Claude Code runs there over SSH (`ssh onidel`), not on the laptop.

## Environment

- Dev: edit in `~/dev/<app>` on the VPS; serve from `/srv/<app>` via systemd + Caddy.
- VPS: Ubuntu 24.04, 4 GB RAM / 2 vCPU / 40 GB disk. Node 22, uv, Caddy, ufw, fail2ban installed.
- Laptop (Windows, 8 GB RAM, no CUDA/Docker/WSL) is a thin client only. Don't propose local Docker builds, model training, or large in-memory dataframes there.
- Model training goes to Colab/Kaggle (free GPU); export the artifact and serve that.
- Python tooling: `uv`.

## Conventions

- Branch: `prod` is the main branch.
- Secrets live in `.env` (gitignored). Never commit, print, or paste values; refer to key names only.
- Keep datasets and model artifacts out of git (gitignored). Disk is limited: ~40 GB on VPS.
- Match the style of surrounding code; keep comments sparse.

## Data sources — terms & attribution

- Maintain `terms-conditions.md` as the register of attribution, license, and usage rules for every external data source or information provider.
- When adding or changing a provider (API, scrape, licensed feed, brand assets), update that file **before** shipping charts or public citations: allowed uses, attribution text/logo rules, and hard prohibitions.
- Summaries in `terms-conditions.md` do not replace the provider’s legal documents; link the primary Terms / Data Platform / brand kit and record a last-reviewed date.

## Commands

Run from `aa_mirror/`:

- `uv sync` — install deps
- `uv run pytest` — tests (no network)
- `uv run aa-mirror smoke` — live API check, 1 request, stores nothing
- `uv run aa-mirror refresh [--dry-run]` — fetch one snapshot (6 requests)
- `uv run aa-mirror status`
- `uv run aa-mirror serve [--port 8765]` — UI on 127.0.0.1

## Maintaining this file

- Add build/test/run commands here once they exist.
- Keep it short and factual; record only what isn't obvious from the code.
- Agent-specific files (`AGENTS.md`, etc.) must only point here, never duplicate content.
