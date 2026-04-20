from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from core.logger import get_logger
from core.models import JobPosting
from sources.base import JobSource, SourceUnavailableError

logger = get_logger(__name__)


class ComputrabajoSource(JobSource):
    source_name = "computrabajo"
    BASE_URL = "https://mx.computrabajo.com"
    SEARCH_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-MX,es;q=0.9",
    }
    REMOTE_KEYWORDS = ("remoto", "remote", "presencial y remoto", "home office")
    EMPLOYMENT_TYPE_KEYWORDS = {
        "tiempo completo": "full-time",
        "medio tiempo": "part-time",
        "por horas": "hourly",
        "beca/prácticas": "internship",
    }

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
            "Computrabajo remote-only filter kept %s of %s jobs",
            len(remote_jobs),
            len(jobs),
        )
        return remote_jobs

    def _fetch_search_results(self) -> str:
        url = self._build_search_url()

        try:
            response = requests.get(
                url,
                headers=self.SEARCH_HEADERS,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 403:
                raise SourceUnavailableError(
                    self.source_name,
                    "Computrabajo blocked the automated query with HTTP 403 Forbidden; the source will be skipped.",
                ) from exc
            if status_code == 429:
                raise SourceUnavailableError(
                    self.source_name,
                    "Computrabajo rate-limited the automated query with HTTP 429 Too Many Requests; the source will be skipped.",
                ) from exc
            raise SourceUnavailableError(
                self.source_name,
                f"Computrabajo returned HTTP {status_code or 'unknown'} during discovery; the source will be skipped.",
            ) from exc
        except requests.Timeout as exc:
            raise SourceUnavailableError(
                self.source_name,
                "Computrabajo timed out during discovery; the source will be skipped.",
            ) from exc
        except requests.ConnectionError as exc:
            raise SourceUnavailableError(
                self.source_name,
                "Computrabajo could not be reached due to a connection error; the source will be skipped.",
            ) from exc
        except requests.RequestException as exc:
            raise SourceUnavailableError(
                self.source_name,
                "Computrabajo request failed during discovery; the source will be skipped.",
            ) from exc

        return response.text

    def _build_search_url(self) -> str:
        query_slug = self._slugify(self.query)
        path = f"/trabajo-de-{query_slug}"

        if self.location:
            path = f"{path}-en-{self._slugify(self.location)}"

        return urljoin(self.BASE_URL, path)

    def _parse_search_results(self, html: str) -> list[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        list_item_urls = self._extract_list_item_urls(soup)
        jobs: list[JobPosting] = []

        for article in soup.select("article[data-offers-grid-offer-item-container]"):
            if not isinstance(article, Tag):
                continue

            job = self._parse_article(article, list_item_urls)
            if job is not None:
                jobs.append(job)

        return jobs

    def _extract_list_item_urls(self, soup: BeautifulSoup) -> dict[str, str]:
        urls_by_external_id: dict[str, str] = {}

        for script in soup.select("script[type='application/ld+json']"):
            if not isinstance(script, Tag) or not script.string:
                continue

            try:
                payload = json.loads(script.string)
            except json.JSONDecodeError:
                continue

            graph_items = payload.get("@graph", []) if isinstance(payload, dict) else []
            if not isinstance(graph_items, list):
                continue

            for item in graph_items:
                if not isinstance(item, dict):
                    continue

                list_items = item.get("itemListElement")
                if not isinstance(list_items, list):
                    continue

                for list_item in list_items:
                    if not isinstance(list_item, dict):
                        continue

                    url = str(list_item.get("url", "")).strip()
                    if not url:
                        continue

                    external_id = self._extract_external_id_from_url(url)
                    if external_id:
                        urls_by_external_id[external_id] = url

        return urls_by_external_id

    def _parse_article(
        self,
        article: Tag,
        list_item_urls: dict[str, str],
    ) -> JobPosting | None:
        external_id = str(article.get("data-id", "")).strip()
        title_link = article.select_one("h2 a.js-o-link")
        if not isinstance(title_link, Tag):
            return None

        title = self._clean_text(title_link.get_text(" ", strip=True))
        href = str(title_link.get("href", "")).strip()
        if not title or not href or not external_id:
            return None

        raw_url = list_item_urls.get(external_id) or urljoin(self.BASE_URL, href.split("#", 1)[0])
        url = raw_url.split("#", 1)[0]
        company = self._extract_company(article)
        location = self._extract_location(article)
        metadata = self._extract_metadata(article)
        salary_text = self._extract_salary(metadata)
        work_mode = self._extract_work_mode(metadata)
        date_posted = self._extract_date_posted(article)
        employment_type = self._infer_employment_type(metadata)
        description = self._build_description_snippet(company, location, salary_text, work_mode)

        normalized_tags = self.build_normalized_tags(
            self.query,
            title,
            company,
            location,
            salary_text,
            work_mode,
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

    def _extract_company(self, article: Tag) -> str | None:
        company_link = article.select_one("[offer-grid-article-company-url]")
        if isinstance(company_link, Tag):
            return self._clean_text(company_link.get_text(" ", strip=True))
        return None

    def _extract_location(self, article: Tag) -> str | None:
        for paragraph in article.select("p.fs16.fc_base.mt5"):
            if not isinstance(paragraph, Tag):
                continue
            classes = set(paragraph.get("class", []))
            if {"dFlex", "vm_fx"}.intersection(classes):
                continue

            location_node = paragraph.select_one("span.mr10")
            if isinstance(location_node, Tag):
                return self._clean_text(location_node.get_text(" ", strip=True))
        return None

    def _extract_metadata(self, article: Tag) -> list[str]:
        metadata: list[str] = []
        for node in article.select("div.fs13.mt15 span.dIB"):
            if not isinstance(node, Tag):
                continue
            text = self._clean_text(node.get_text(" ", strip=True))
            if text:
                metadata.append(text)
        return metadata

    @staticmethod
    def _extract_salary(metadata: list[str]) -> str | None:
        for value in metadata:
            if "$" in value or "mensual" in value.lower():
                return value
        return None

    def _extract_work_mode(self, metadata: list[str]) -> str | None:
        for value in metadata:
            lowered = value.lower()
            if any(keyword in lowered for keyword in self.REMOTE_KEYWORDS):
                return value
        return None

    def _extract_date_posted(self, article: Tag) -> str | None:
        node = article.select_one("p.fs13.fc_aux.mt15")
        if isinstance(node, Tag):
            return self._clean_text(node.get_text(" ", strip=True))
        return None

    def _infer_employment_type(self, metadata: list[str]) -> str | None:
        joined = " ".join(value.lower() for value in metadata)
        for keyword, value in self.EMPLOYMENT_TYPE_KEYWORDS.items():
            if keyword in joined:
                return value
        return None

    @staticmethod
    def _build_description_snippet(*parts: str | None) -> str | None:
        snippet = " | ".join(part for part in parts if part)
        return snippet or None

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
        return any(keyword in remote_text for keyword in self.REMOTE_KEYWORDS)

    @staticmethod
    def _extract_external_id_from_url(url: str) -> str:
        path = urlparse(url).path.rstrip("/")
        match = re.search(r"-([A-Z0-9]+)$", path, re.IGNORECASE)
        return match.group(1).upper() if match else ""

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @staticmethod
    def _slugify(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
        return slug or "empleo"
