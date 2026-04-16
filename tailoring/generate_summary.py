from __future__ import annotations

from core.models import JobPosting
from tailoring.tailor_resume import TailoredResumeResult


def generate_fit_summary_markdown(
    job: JobPosting,
    tailored_resume: TailoredResumeResult,
) -> str:
    lines: list[str] = []

    lines.append("# Tailoring Summary")
    lines.append("")
    lines.append("## Target Job")
    lines.append(f"- Job ID: {job.id if job.id is not None else 'N/A'}")
    lines.append(f"- Company: {job.company}")
    lines.append(f"- Title: {job.title}")
    if job.location:
        lines.append(f"- Location: {job.location}")
    if job.score is not None:
        lines.append(f"- Score: {job.score} ({job.score_label or 'unlabeled'})")
    lines.append(f"- URL: {job.url}")
    lines.append("")

    lines.append("## Match Signals")
    if tailored_resume.matched_skills:
        lines.append(
            f"- Matched skills already present in the master resume: {', '.join(tailored_resume.matched_skills[:8])}"
        )
    else:
        lines.append("- No direct skill matches were detected from the current master resume content.")

    if tailored_resume.prioritized_experience_ids:
        lines.append(
            f"- Prioritized experience entries: {', '.join(tailored_resume.prioritized_experience_ids)}"
        )
    if tailored_resume.prioritized_project_ids:
        lines.append(
            f"- Prioritized project entries: {', '.join(tailored_resume.prioritized_project_ids)}"
        )
    if tailored_resume.extracted_keywords:
        lines.append(
            f"- Vacancy keywords considered for tailoring: {', '.join(tailored_resume.extracted_keywords[:10])}"
        )
    lines.append("")

    lines.append("## Gaps And Cautions")
    if tailored_resume.missing_keywords:
        lines.append(
            f"- Mentioned in the vacancy but not evidenced in the master resume: {', '.join(tailored_resume.missing_keywords[:8])}"
        )
    else:
        lines.append("- No major missing keywords were flagged from the extracted job signals.")
    lines.append("- The tailored resume only reorders and emphasizes existing resume content.")
    lines.append("- No skills, experience, achievements, or metrics were invented.")
    lines.append("")

    lines.append("## Applied Decisions")
    lines.append("- Reordered skills so the strongest direct matches appear earlier.")
    lines.append("- Ranked experience and project bullets by overlap with job keywords.")
    lines.append("- Updated the professional summary using only facts already present in the master resume.")
    lines.append("")

    return "\n".join(lines)
