from __future__ import annotations

import sqlite3
from pathlib import Path


def initialize_database(database_path: str) -> None:
    db_path = Path(database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS job_postings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                employment_type TEXT,
                seniority TEXT,
                salary_text TEXT,
                url TEXT NOT NULL,
                description TEXT,
                date_posted TEXT,
                discovered_at TEXT NOT NULL,
                normalized_tags TEXT NOT NULL,
                is_relevant INTEGER NOT NULL DEFAULT 0,
                relevance_reason TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                source_board TEXT,
                raw_location TEXT,
                notified_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, external_id),
                UNIQUE(url)
            )
            """
        )
        connection.commit()
    finally:
        connection.close()