from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from core.models import JobPosting


class JobRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def job_exists(self, job: JobPosting) -> bool:
        with self._get_connection() as connection:
            cursor = connection.cursor()

            return self._job_exists_with_cursor(cursor, job)

    def insert_job_if_not_exists(self, job: JobPosting) -> bool:
        with self._get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO job_postings (
                    source,
                    external_id,
                    title,
                    company,
                    location,
                    employment_type,
                    seniority,
                    salary_text,
                    url,
                    description,
                    date_posted,
                    discovered_at,
                    normalized_tags,
                    is_relevant,
                    relevance_reason,
                    score,
                    score_label,
                    score_reasons,
                    status,
                    source_board,
                    raw_location
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.source,
                    job.external_id,
                    job.title,
                    job.company,
                    job.location,
                    job.employment_type,
                    job.seniority,
                    job.salary_text,
                    str(job.url),
                    job.description,
                    job.date_posted,
                    job.discovered_at.isoformat(),
                    json.dumps(job.normalized_tags, ensure_ascii=False),
                    int(job.is_relevant),
                    job.relevance_reason,
                    job.score,
                    job.score_label,
                    json.dumps(job.score_reasons, ensure_ascii=False),
                    job.status,
                    job.source_board,
                    job.raw_location,
                ),
            )
            return cursor.rowcount > 0

    def mark_as_notified(self, job: JobPosting) -> None:
        with self._get_connection() as connection:
            cursor = connection.cursor()
            notification_timestamp = datetime.now(timezone.utc).isoformat()
            unique_identifier = job.external_id.strip()

            if unique_identifier:
                cursor.execute(
                    """
                    UPDATE job_postings
                    SET status = ?, notified_at = ?
                    WHERE source = ? AND external_id = ?
                    """,
                    (
                        "notified",
                        notification_timestamp,
                        job.source,
                        unique_identifier,
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE job_postings
                    SET status = ?, notified_at = ?
                    WHERE url = ?
                    """,
                    (
                        "notified",
                        notification_timestamp,
                        str(job.url),
                    ),
                )

    def list_new_jobs(self) -> list[dict]:
        with self._get_connection() as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT *
                FROM job_postings
                WHERE status = 'new'
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def _job_exists_with_cursor(cursor: sqlite3.Cursor, job: JobPosting) -> bool:
        unique_identifier = job.external_id.strip()

        if unique_identifier:
            cursor.execute(
                """
                SELECT 1
                FROM job_postings
                WHERE source = ? AND external_id = ?
                LIMIT 1
                """,
                (job.source, unique_identifier),
            )
            if cursor.fetchone():
                return True

        cursor.execute(
            """
            SELECT 1
            FROM job_postings
            WHERE url = ?
            LIMIT 1
            """,
            (str(job.url),),
        )
        return cursor.fetchone() is not None