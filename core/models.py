from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


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
