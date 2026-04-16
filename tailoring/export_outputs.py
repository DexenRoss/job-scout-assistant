from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from core.models import JobPosting

DEFAULT_OUTPUT_DIR = Path("data/outputs")


@dataclass(frozen=True)
class ExportedTailoringFiles:
    resume_path: Path
    summary_path: Path
    metadata_path: Path


def export_tailoring_outputs(
    *,
    job: JobPosting,
    tailored_resume_markdown: str,
    summary_markdown: str,
    metadata: dict[str, object],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> ExportedTailoringFiles:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    file_stem = _build_output_stem(job)
    resume_path = destination / f"{file_stem}__resume.md"
    summary_path = destination / f"{file_stem}__summary.md"
    metadata_path = destination / f"{file_stem}__metadata.json"

    resume_path.write_text(tailored_resume_markdown, encoding="utf-8")
    summary_path.write_text(summary_markdown, encoding="utf-8")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ExportedTailoringFiles(
        resume_path=resume_path,
        summary_path=summary_path,
        metadata_path=metadata_path,
    )


def _build_output_stem(job: JobPosting) -> str:
    company_slug = _slugify(job.company)
    title_slug = _slugify(job.title)
    identifier = f"job-{job.id}" if job.id is not None else _slugify(job.external_id or "job")
    return f"{company_slug}__{title_slug}__{identifier}"


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "item"
