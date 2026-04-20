from __future__ import annotations

import re
from abc import ABC, abstractmethod

from core.models import JobPosting


class JobSource(ABC):
    source_name: str

    @abstractmethod
    def fetch_jobs(self) -> list[JobPosting]:
        raise NotImplementedError

    @staticmethod
    def tokenize(text: str) -> list[str]:
        cleaned = re.sub(r"[\-/,|()]+", " ", text.lower())
        return [part.strip() for part in cleaned.split() if part.strip()]

    @classmethod
    def build_normalized_tags(cls, *values: str | None) -> list[str]:
        tags: list[str] = []
        for value in values:
            if value:
                tags.extend(cls.tokenize(value))
        return sorted({tag for tag in tags if tag})
