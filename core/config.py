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


def _parse_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    return int(value.strip())


@dataclass(frozen=True)
class Settings:
    discord_webhook_url: str | None
    database_path: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    scoring_enabled: bool
    scoring_min_notify_score: int
    preferred_keywords: list[str]
    preferred_locations: list[str]
    seniority_preference: str | None
    greenhouse_enabled: bool
    greenhouse_company_boards: list[str]
    greenhouse_include_content: bool
    indeed_enabled: bool
    indeed_query: str | None
    indeed_location: str | None
    indeed_remote_only: bool
    occ_enabled: bool
    computrabajo_enabled: bool
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
        scoring_enabled=_parse_bool(os.getenv("SCORING_ENABLED"), default=True),
        scoring_min_notify_score=_parse_int(
            os.getenv("SCORING_MIN_NOTIFY_SCORE"),
            default=60,
        ),
        preferred_keywords=_parse_csv(os.getenv("PREFERRED_KEYWORDS")),
        preferred_locations=_parse_csv(os.getenv("PREFERRED_LOCATIONS")),
        seniority_preference=(
            os.getenv("SENIORITY_PREFERENCE", "").strip().lower() or None
        ),
        greenhouse_enabled=_parse_bool(os.getenv("GREENHOUSE_ENABLED"), default=True),
        greenhouse_company_boards=_parse_csv(os.getenv("GREENHOUSE_COMPANY_BOARDS")),
        greenhouse_include_content=_parse_bool(
            os.getenv("GREENHOUSE_INCLUDE_CONTENT"), default=True
        ),
        indeed_enabled=_parse_bool(os.getenv("INDEED_ENABLED"), default=False),
        indeed_query=os.getenv("INDEED_QUERY", "").strip() or None,
        indeed_location=os.getenv("INDEED_LOCATION", "").strip() or None,
        indeed_remote_only=_parse_bool(os.getenv("INDEED_REMOTE_ONLY"), default=False),
        occ_enabled=_parse_bool(os.getenv("OCC_ENABLED"), default=False),
        computrabajo_enabled=_parse_bool(
            os.getenv("COMPUTRABAJO_ENABLED"),
            default=False,
        ),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
