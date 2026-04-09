from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    discord_webhook_url: str | None
    database_path: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    greenhouse_enabled: bool
    greenhouse_company_boards: list[str]
    greenhouse_include_content: bool
    request_timeout_seconds: float
    log_level: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()

    default_db_path = str(Path("data") / "jobs.db")

    return Settings(
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        database_path=os.getenv("DATABASE_PATH", default_db_path),
        include_keywords=_parse_csv(os.getenv("INCLUDE_KEYWORDS")),
        exclude_keywords=_parse_csv(os.getenv("EXCLUDE_KEYWORDS")),
        greenhouse_enabled=_parse_bool(os.getenv("GREENHOUSE_ENABLED"), default=True),
        greenhouse_company_boards=_parse_csv(os.getenv("GREENHOUSE_COMPANY_BOARDS")),
        greenhouse_include_content=_parse_bool(
            os.getenv("GREENHOUSE_INCLUDE_CONTENT"), default=True
        ),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )