from __future__ import annotations

from core.models import JobPosting


def build_discord_message(job: JobPosting) -> dict:
    location = job.location or "Not specified"
    relevance_reason = job.relevance_reason or "Relevant by current filter"
    content = (
        f"**{job.title}**\n"
        f"Company: {job.company}\n"
        f"Location: {location}\n"
        f"Source: {job.source}\n"
        f"Reason: {relevance_reason}\n"
        f"Link: {job.url}"
    )
    return {"content": content}