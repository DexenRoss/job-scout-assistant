from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

DEDUP_NORMALIZE_PATTERN = re.compile(r"\s+")


class JobPosting(BaseModel):
    id: int | None = None
    source: str
    external_id: str
    title: str
    company: str
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    salary_text: str | None = None
    url: HttpUrl
    description: str | None = None
    date_posted: str | None = None
    discovered_at: datetime
    normalized_tags: list[str] = Field(default_factory=list)
    is_relevant: bool = False
    relevance_reason: str | None = None
    score: int | None = None
    score_label: str | None = None
    score_reasons: list[str] = Field(default_factory=list)
    status: Literal["new", "notified", "ignored"] = "new"
    source_board: str | None = None
    raw_location: str | None = None

    def unique_key(self) -> tuple[str, str]:
        fallback = self.external_id.strip() if self.external_id.strip() else str(self.url)
        return self.source, fallback

    def deduplication_fingerprint(self) -> tuple[str, str, str] | None:
        title = self._normalize_for_dedup(self.title)
        company = self._normalize_for_dedup(self.company)
        location = self._normalize_for_dedup(self.location or self.raw_location)

        if not title or not company or not location:
            return None

        return title, company, location

    @staticmethod
    def _normalize_for_dedup(value: str | None) -> str:
        if not value:
            return ""
        return DEDUP_NORMALIZE_PATTERN.sub(" ", value.lower().strip())
