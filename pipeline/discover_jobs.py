from __future__ import annotations

from core.config import Settings
from core.logger import get_logger
from core.models import JobPosting
from sources.base import SourceUnavailableError
from sources.registry import build_source_bindings

logger = get_logger(__name__)


def discover_jobs(settings: Settings) -> list[JobPosting]:
    jobs: list[JobPosting] = []

    for binding in build_source_bindings(settings):
        if not binding.enabled or binding.source is None:
            logger.info(
                "Skipping source '%s': %s",
                binding.name,
                binding.reason or "disabled by configuration",
            )
            continue

        try:
            source_jobs = binding.source.fetch_jobs()
        except SourceUnavailableError as exc:
            logger.warning("Skipping source '%s': %s", binding.name, exc)
            continue
        except Exception as exc:
            logger.exception("Source '%s' failed during discovery: %s", binding.name, exc)
            continue

        logger.info("Source '%s' discovered %s jobs", binding.name, len(source_jobs))
        jobs.extend(source_jobs)

    return jobs
