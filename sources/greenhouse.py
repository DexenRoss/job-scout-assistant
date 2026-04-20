from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from core.logger import get_logger
from core.models import JobPosting
from sources.base import JobSource

logger = get_logger(__name__)


class GreenhouseSource(JobSource):
    source_name = "greenhouse"
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(
        self,
        board_tokens: list[str],
        timeout_seconds: float = 20.0,
        include_content: bool = True,
    ) -> None:
        self.board_tokens = board_tokens
        self.timeout_seconds = timeout_seconds
        self.include_content = include_content

    def fetch_jobs(self) -> list[JobPosting]:
        jobs: list[JobPosting] = []

        for board_token in self.board_tokens:
            try:
                board_jobs = self._fetch_board_jobs(board_token)
                jobs.extend(board_jobs)
                logger.info(
                    "Greenhouse board '%s' returned %s jobs",
                    board_token,
                    len(board_jobs),
                )
            except Exception as exc:
                logger.exception(
                    "Failed to fetch jobs from Greenhouse board '%s': %s",
                    board_token,
                    exc,
                )

        return jobs

    def _fetch_board_jobs(self, board_token: str) -> list[JobPosting]:
        params = {"content": "true"} if self.include_content else {}
        url = f"{self.BASE_URL}/{board_token}/jobs"

        response = requests.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()

        payload = response.json()
        raw_jobs = payload.get("jobs", [])

        normalized_jobs: list[JobPosting] = []
        for raw_job in raw_jobs:
            job = self._map_job(raw_job, board_token)
            normalized_jobs.append(job)

        return normalized_jobs

    def _map_job(self, raw_job: dict[str, Any], board_token: str) -> JobPosting:
        metadata = raw_job.get("metadata", []) or []

        title = raw_job.get("title", "").strip()
        company = board_token
        location = self._extract_location(raw_job)
        employment_type = self._extract_metadata_value(metadata, ["employment type", "type"])
        seniority = self._extract_metadata_value(metadata, ["seniority", "experience level", "level"])
        salary_text = self._extract_metadata_value(metadata, ["salary", "compensation", "pay range"])
        description = raw_job.get("content")

        metadata_values: list[str] = []
        for item in metadata:
            name = str(item.get("name", "")).strip()
            value = item.get("value")

            if name:
                metadata_values.append(name)

            if isinstance(value, str) and value.strip():
                metadata_values.append(value.strip())
            elif isinstance(value, list):
                metadata_values.extend(
                    str(entry).strip() for entry in value if str(entry).strip()
                )

        normalized_tags = self.build_normalized_tags(
            title,
            company,
            location,
            employment_type,
            seniority,
            *metadata_values,
        )

        external_id = str(raw_job.get("id", "")).strip()
        if not external_id:
            external_id = raw_job.get("absolute_url", "").strip()

        return JobPosting(
            source=self.source_name,
            external_id=external_id,
            title=title,
            company=company,
            location=location,
            employment_type=employment_type,
            seniority=seniority,
            salary_text=salary_text,
            url=raw_job["absolute_url"],
            description=description,
            date_posted=raw_job.get("updated_at"),
            discovered_at=datetime.now(timezone.utc),
            normalized_tags=normalized_tags,
            source_board=board_token,
            raw_location=location,
        )

    @staticmethod
    def _extract_location(raw_job: dict[str, Any]) -> str | None:
        location_data = raw_job.get("location")
        if isinstance(location_data, dict):
            name = location_data.get("name")
            return name.strip() if isinstance(name, str) and name.strip() else None
        return None

    @staticmethod
    def _extract_metadata_value(
        metadata: list[dict[str, Any]],
        accepted_names: list[str],
    ) -> str | None:
        normalized_names = {name.lower() for name in accepted_names}

        for item in metadata:
            key = str(item.get("name", "")).strip().lower()
            if key not in normalized_names:
                continue

            value = item.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()

            if isinstance(value, list):
                values = [str(v).strip() for v in value if str(v).strip()]
                if values:
                    return ", ".join(values)

        return None
