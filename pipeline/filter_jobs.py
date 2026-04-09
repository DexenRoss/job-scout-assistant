from __future__ import annotations

from core.models import JobPosting


class JobFilter:
    def __init__(self, include_keywords: list[str], exclude_keywords: list[str]) -> None:
        self.include_keywords = [item.lower() for item in include_keywords]
        self.exclude_keywords = [item.lower() for item in exclude_keywords]

    def evaluate(self, job: JobPosting) -> JobPosting:
        haystack = self._build_search_text(job)

        matched_exclude = self._find_first_match(haystack, self.exclude_keywords)
        if matched_exclude:
            job.is_relevant = False
            job.relevance_reason = f"Excluded by keyword: {matched_exclude}"
            job.status = "ignored"
            return job

        matched_include = self._find_first_match(haystack, self.include_keywords)
        if matched_include:
            job.is_relevant = True
            job.relevance_reason = f"Matched include keyword: {matched_include}"
            job.status = "new"
            return job

        job.is_relevant = False
        job.relevance_reason = "No include keywords matched"
        job.status = "ignored"
        return job

    @staticmethod
    def _build_search_text(job: JobPosting) -> str:
        fields = [
            job.title,
            job.description or "",
            job.company,
            " ".join(job.normalized_tags),
        ]
        return " ".join(fields).lower()

    @staticmethod
    def _find_first_match(haystack: str, keywords: list[str]) -> str | None:
        for keyword in keywords:
            if keyword and keyword in haystack:
                return keyword
        return None