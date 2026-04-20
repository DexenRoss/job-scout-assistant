from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from core.logger import get_logger
from core.models import JobPosting
from sources.base import JobSource

logger = get_logger(__name__)


class IndeedSource(JobSource):
    source_name = "indeed"
    BASE_URL = "https://www.indeed.com"
    SEARCH_PATH = "/jobs"
    SEARCH_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    REMOTE_KEYWORDS = ("remote", "remoto", "work from home", "wfh", "anywhere", "distributed")
    NON_REMOTE_KEYWORDS = ("hybrid", "on-site", "onsite", "in person", "office")

    def __init__(
        self,
        query: str,
        location: str | None = None,
        remote_only: bool = False,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.query = query.strip()
        self.location = location.strip() if location else None
        self.remote_only = remote_only
        self.timeout_seconds = timeout_seconds

    def fetch_jobs(self) -> list[JobPosting]:
        html = self._fetch_search_results()
        jobs = self._parse_search_results(html)

        if not self.remote_only:
            return jobs

        remote_jobs = [job for job in jobs if self._is_remote_job(job)]
        logger.info(
            "Indeed remote-only filter kept %s of %s jobs",
            len(remote_jobs),
            len(jobs),
        )
        return remote_jobs

    def _fetch_search_results(self) -> str:
        params = {
            "q": self.query,
            "sort": "date",
        }
        if self.location:
            params["l"] = self.location

        response = requests.get(
            urljoin(self.BASE_URL, self.SEARCH_PATH),
            params=params,
            headers=self.SEARCH_HEADERS,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.text

    def _parse_search_results(self, html: str) -> list[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        anchors = self._find_title_anchors(soup)
        jobs: list[JobPosting] = []
        seen_external_ids: set[str] = set()

        for anchor in anchors:
            job = self._parse_job_from_anchor(anchor)
            if job is None:
                continue

            if job.external_id in seen_external_ids:
                continue

            seen_external_ids.add(job.external_id)
            jobs.append(job)

        return jobs

    def _find_title_anchors(self, soup: BeautifulSoup) -> list[Tag]:
        selectors = (
            "a.tapItem",
            "h2.jobTitle a",
            "a.jcs-JobTitle",
            "a[data-jk]",
        )
        anchors: list[Tag] = []
        seen_nodes: set[int] = set()

        for selector in selectors:
            for anchor in soup.select(selector):
                if not isinstance(anchor, Tag):
                    continue
                href = anchor.get("href", "")
                if "jk=" not in href:
                    continue
                node_id = id(anchor)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                anchors.append(anchor)

        return anchors

    def _parse_job_from_anchor(self, anchor: Tag) -> JobPosting | None:
        href = anchor.get("href", "").strip()
        title_node = anchor.select_one("h2.jobTitle")
        title = self._clean_text(
            title_node.get_text(" ", strip=True) if isinstance(title_node, Tag) else anchor.get_text(" ", strip=True)
        )
        if not href or not title:
            return None

        url = self._absolute_job_url(href)
        external_id = self._extract_external_id(url)
        if not external_id:
            return None

        card = self._find_card_container(anchor)
        company = self._extract_first_text(
            card,
            selectors=[
                "[data-testid='company-name']",
                ".companyName",
                "span.companyName",
            ],
        )
        location = self._extract_first_text(
            card,
            selectors=[
                "[data-testid='text-location']",
                ".companyLocation",
                "div.companyLocation",
            ],
        )
        salary_text = self._extract_first_text(
            card,
            selectors=[
                ".salary-snippet-container",
                ".salary-snippet",
                ".estimated-salary-container",
            ],
        )
        description = self._extract_first_text(
            card,
            selectors=[
                ".job-snippet",
                "[data-testid='job-snippet']",
            ],
        )
        date_posted = self._extract_first_text(
            card,
            selectors=[
                "[data-testid='myJobsStateDate']",
                ".date",
                ".metadata.turnstileId",
            ],
        )
        employment_type = self._infer_employment_type(
            values=[salary_text, description, location],
        )

        normalized_tags = self.build_normalized_tags(
            self.query,
            title,
            company,
            location,
            salary_text,
            description,
            employment_type,
        )

        return JobPosting(
            source=self.source_name,
            external_id=external_id,
            title=title,
            company=company or "Unknown company",
            location=location,
            employment_type=employment_type,
            seniority=None,
            salary_text=salary_text,
            url=url,
            description=description,
            date_posted=date_posted,
            discovered_at=datetime.now(timezone.utc),
            normalized_tags=normalized_tags,
            source_board=self.query,
            raw_location=location,
        )

    def _find_card_container(self, anchor: Tag) -> Tag:
        for candidate in [anchor, *anchor.parents]:
            if not isinstance(candidate, Tag):
                continue

            classes = set(candidate.get("class", []))
            if candidate.name == "a" and "tapItem" in classes:
                return candidate
            if candidate.get("data-jk"):
                return candidate
            if classes.intersection(
                {
                    "job_seen_beacon",
                    "cardOutline",
                    "slider_item",
                    "jobsearch-SerpJobCard",
                }
            ):
                return candidate

        return anchor

    def _absolute_job_url(self, href: str) -> str:
        return urljoin(self.BASE_URL, href)

    @staticmethod
    def _extract_external_id(url: str) -> str:
        parsed = urlparse(url)
        job_keys = parse_qs(parsed.query).get("jk", [])
        return job_keys[0].strip() if job_keys else ""

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    def _extract_first_text(self, node: Tag, selectors: Iterable[str]) -> str | None:
        for selector in selectors:
            candidate = node.select_one(selector)
            if not isinstance(candidate, Tag):
                continue
            text = self._clean_text(candidate.get_text(" ", strip=True))
            if text:
                return text
        return None

    @staticmethod
    def _infer_employment_type(values: Iterable[str | None]) -> str | None:
        joined = " ".join(value.lower() for value in values if value)
        if "full-time" in joined:
            return "full-time"
        if "part-time" in joined:
            return "part-time"
        if "contract" in joined:
            return "contract"
        if "temporary" in joined:
            return "temporary"
        return None

    def _is_remote_job(self, job: JobPosting) -> bool:
        remote_text = " ".join(
            part.lower()
            for part in [
                job.title,
                job.location or "",
                job.raw_location or "",
                job.description or "",
                " ".join(job.normalized_tags),
            ]
            if part
        )
        has_remote_signal = any(keyword in remote_text for keyword in self.REMOTE_KEYWORDS)
        has_non_remote_signal = any(
            keyword in remote_text for keyword in self.NON_REMOTE_KEYWORDS
        )
        return has_remote_signal and not has_non_remote_signal
