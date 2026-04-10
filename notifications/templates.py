from __future__ import annotations

from core.models import JobPosting


def build_discord_message(job: JobPosting) -> dict:
    location = job.location or "Not specified"
    score = f"{job.score}/100" if job.score is not None else "n/a"
    score_label = job.score_label or "unscored"
    top_reasons = job.score_reasons[:3]
    reasons_text = " | ".join(top_reasons) if top_reasons else (job.relevance_reason or "Relevant by current filter")
    content = (
        f"**{job.title}** at **{job.company}**\n"
        f"Score: {score} ({score_label})\n"
        f"Location: {location}\n"
        f"Why: {reasons_text}\n"
        f"Link: {job.url}"
    )
    return {"content": content}
