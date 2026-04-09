from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import JobPosting


class JobSource(ABC):
    source_name: str

    @abstractmethod
    def fetch_jobs(self) -> list[JobPosting]:
        raise NotImplementedError