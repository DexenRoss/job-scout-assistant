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
                score INTEGER,
                score_label TEXT,
                score_reasons TEXT NOT NULL DEFAULT '[]',
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
        _ensure_column(cursor, "job_postings", "score", "INTEGER")
        _ensure_column(cursor, "job_postings", "score_label", "TEXT")
        _ensure_column(cursor, "job_postings", "score_reasons", "TEXT NOT NULL DEFAULT '[]'")
        connection.commit()
    finally:
        connection.close()


def _ensure_column(
    cursor: sqlite3.Cursor,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name in existing_columns:
        return

    cursor.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
    )
