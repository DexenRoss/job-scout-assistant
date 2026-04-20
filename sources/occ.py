from __future__ import annotations

from core.logger import get_logger
from core.models import JobPosting
from sources.base import JobSource

logger = get_logger(__name__)


class OccSource(JobSource):
    source_name = "occ"

    def fetch_jobs(self) -> list[JobPosting]:
        logger.warning(
            "OCC source is enabled but still a stub for Sprint 4A; skipping fetch"
        )
        return []
