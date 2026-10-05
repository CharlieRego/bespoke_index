# bespoke_index
Bespoke AI Model Indices

## AA Study Mirror (private)

`aa_mirror/` is an internal-only study copy of the Artificial Analysis free-tier Data API: LLM benchmarks/indices, pricing and speed, plus the media (text-to-image, image-editing, text-to-speech, text-to-video, image-to-video) leaderboards. Each refresh stores a timestamped snapshot in SQLite so history accumulates; a small FastAPI app serves sortable leaderboards, charts, per-model history and snapshot comparison.

Private use only (see `terms-conditions.md`): never deploy it publicly, add exports, or commit fetched data. Source: Artificial Analysis (artificialanalysis.ai).

### Setup

Requires `uv`. The API key is read server-side from `AA_MAIN_PROJ_KEY`, either from the environment or a `.env` file found by walking up from the current directory (format: `AA_MAIN_PROJ_KEY=value`, no spaces or quotes; see `shelf-notes.md`).

```sh
cd aa_mirror
uv sync
uv run pytest                      # synthetic fixtures only, no network
uv run aa-mirror smoke             # live check: 1 request, parses it, reports schema drift, stores nothing
uv run aa-mirror refresh           # fetch one snapshot (6 requests) into ./data/aa_mirror.sqlite3
uv run aa-mirror refresh --dry-run # show endpoints and lock/cooldown/budget state; no requests
uv run aa-mirror status
uv run aa-mirror serve             # http://127.0.0.1:8765
```

Settings (env vars): `AA_DATA_DIR` (default `./data`), `AA_COOLDOWN_SECONDS` (900), `AA_DAILY_REQUEST_BUDGET` (500, below AA's 1,000/day), `AA_STALE_LOCK_SECONDS` (600).

### Refreshing

- **On demand:** the "Refresh now" button POSTs to `/api/refresh`, which runs the same job as the CLI in a background thread. The header bar shows last refreshed time, the last run's result and requests used in the last 24h.
- **Guards:** a SQLite `BEGIN IMMEDIATE` lock allows one run at a time across the web process and the timer (409 if busy). A cooldown (429) follows any run that made requests, and a rolling 24h request budget is enforced. Runs left `running` longer than the stale timeout are marked failed and the lock is released.
- **Scheduled:** `deploy/aa-mirror-refresh.timer` runs `aa-mirror refresh --trigger timer` daily at 06:30 Sydney time.

### Deploying on the VPS (manual; not done automatically)

```sh
# as your user on the VPS
cd ~/dev/bespoke_index && git pull
sudo useradd --system --home /srv/aa-mirror --shell /usr/sbin/nologin aa-mirror
sudo mkdir -p /srv/aa-mirror /etc/aa-mirror
sudo rsync -a --delete --exclude .venv --exclude .uv-cache --exclude data aa_mirror/ /srv/aa-mirror/
sudo chown -R aa-mirror:aa-mirror /srv/aa-mirror
sudo -u aa-mirror env UV_CACHE_DIR=/srv/aa-mirror/.uv-cache "$(command -v uv)" sync --frozen --no-dev --project /srv/aa-mirror
sudo install -m 640 -o root -g aa-mirror aa_mirror/deploy/aa-mirror.env.example /etc/aa-mirror/aa-mirror.env
sudoedit /etc/aa-mirror/aa-mirror.env            # set AA_MAIN_PROJ_KEY
sudo cp aa_mirror/deploy/aa-mirror.service aa_mirror/deploy/aa-mirror-refresh.service aa_mirror/deploy/aa-mirror-refresh.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aa-mirror.service aa-mirror-refresh.timer
sudo systemctl start aa-mirror-refresh.service   # first snapshot now
systemctl list-timers aa-mirror-refresh.timer
journalctl -u aa-mirror-refresh.service -n 20
```

Access: preferably keep it on localhost and use `ssh -L 8765:127.0.0.1:8765 onidel`, then open http://localhost:8765. If a subdomain is wanted, use `deploy/Caddyfile.snippet` (basic auth is mandatory).

Trigger a refresh from the shell: `sudo systemctl start aa-mirror-refresh.service`, or through the tunnel: `curl -X POST -H 'X-Requested-With: aa-mirror' http://localhost:8765/api/refresh`.
