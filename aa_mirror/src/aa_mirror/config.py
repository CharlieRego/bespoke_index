import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

KEY_ENV = "AA_MAIN_PROJ_KEY"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    base_url: str = "https://artificialanalysis.ai"
    cooldown_seconds: int = 900
    daily_request_budget: int = 500
    stale_lock_seconds: int = 600
    http_timeout: float = 30.0

    @property
    def db_path(self) -> Path:
        return self.data_dir / "aa_mirror.sqlite3"

    @staticmethod
    def api_key() -> str | None:
        key = os.environ.get(KEY_ENV, "").strip()
        return key or None


def load_settings() -> Settings:
    load_dotenv(find_dotenv(usecwd=True))
    env = os.environ.get
    return Settings(
        data_dir=Path(env("AA_DATA_DIR", "data")).resolve(),
        base_url=env("AA_BASE_URL", "https://artificialanalysis.ai").rstrip("/"),
        cooldown_seconds=int(env("AA_COOLDOWN_SECONDS", "900")),
        daily_request_budget=int(env("AA_DAILY_REQUEST_BUDGET", "500")),
        stale_lock_seconds=int(env("AA_STALE_LOCK_SECONDS", "600")),
    )
