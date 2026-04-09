from __future__ import annotations

from core.config import Settings
from core.logger import get_logger
from core.models import JobPosting
from sources.greenhouse import GreenhouseSource

logger = get_logger(__name__)


def discover_jobs(settings: Settings) -> list[JobPosting]:
    jobs: list[JobPosting] = []

    if settings.greenhouse_enabled:
        if not settings.greenhouse_company_boards:
            logger.warning(
                "GREENHOUSE_ENABLED is true but GREENHOUSE_COMPANY_BOARDS is empty"
            )
        else:
            greenhouse_source = GreenhouseSource(
                board_tokens=settings.greenhouse_company_boards,
                timeout_seconds=settings.request_timeout_seconds,
                include_content=settings.greenhouse_include_content,
            )
            jobs.extend(greenhouse_source.fetch_jobs())

    return jobs