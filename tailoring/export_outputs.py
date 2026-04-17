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
    resume_markdown_path: Path
    summary_markdown_path: Path
    metadata_json_path: Path
    resume_pdf_path: Path | None
    warnings: list[str]


def export_tailoring_outputs(
    *,
    job: JobPosting,
    tailored_resume_markdown: str,
    summary_markdown: str,
    metadata: dict[str, object],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    generate_pdf: bool = True,
) -> ExportedTailoringFiles:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    file_stem = _build_output_stem(job)
    resume_markdown_path = destination / f"{file_stem}__resume.md"
    summary_markdown_path = destination / f"{file_stem}__summary.md"
    metadata_json_path = destination / f"{file_stem}__metadata.json"
    resume_pdf_path = destination / f"{file_stem}__resume.pdf"

    resume_markdown_path.write_text(tailored_resume_markdown, encoding="utf-8")
    summary_markdown_path.write_text(summary_markdown, encoding="utf-8")

    warnings: list[str] = []
    exported_resume_pdf_path: Path | None = None
    if generate_pdf:
        try:
            _render_resume_pdf_from_markdown(
                tailored_resume_markdown,
                resume_pdf_path,
            )
            exported_resume_pdf_path = resume_pdf_path
        except ModuleNotFoundError:
            warnings.append(
                "PDF export skipped because `reportlab` is not installed in the current environment."
            )
        except Exception as exc:
            warnings.append(f"PDF export skipped due to an unexpected error: {exc}")

    metadata_payload = dict(metadata)
    metadata_payload["export"] = {
        "resume_markdown_path": str(resume_markdown_path),
        "summary_markdown_path": str(summary_markdown_path),
        "metadata_json_path": str(metadata_json_path),
        "resume_pdf_path": str(exported_resume_pdf_path) if exported_resume_pdf_path else None,
        "warnings": warnings,
    }
    metadata_json_path.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ExportedTailoringFiles(
        resume_markdown_path=resume_markdown_path,
        summary_markdown_path=summary_markdown_path,
        metadata_json_path=metadata_json_path,
        resume_pdf_path=exported_resume_pdf_path,
        warnings=warnings,
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


def _render_resume_pdf_from_markdown(markdown_text: str, output_path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        spaceAfter=8,
        textColor=colors.black,
    )
    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.black,
    )
    subheading_style = ParagraphStyle(
        "ResumeSubHeading",
        parent=styles["Heading3"],
        fontSize=10.5,
        leading=13,
        spaceBefore=6,
        spaceAfter=3,
        textColor=colors.black,
    )
    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=12,
        spaceAfter=3,
        textColor=colors.black,
    )
    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-6,
    )

    story: list[object] = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        escaped = (
            line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        if line.startswith("# "):
            story.append(Paragraph(escaped[2:], title_style))
            continue
        if line.startswith("## "):
            story.append(Paragraph(escaped[3:], heading_style))
            continue
        if line.startswith("### "):
            story.append(Paragraph(escaped[4:], subheading_style))
            continue
        if line.startswith("- "):
            story.append(Paragraph(escaped[2:], bullet_style, bulletText="•"))
            continue
        story.append(Paragraph(escaped, body_style))

    doc.build(story)
