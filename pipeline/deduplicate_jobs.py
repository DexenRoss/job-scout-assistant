from __future__ import annotations

from core.models import JobPosting
from storage.repositories import JobRepository


def split_new_and_existing_jobs(
    jobs: list[JobPosting],
    repository: JobRepository,
) -> tuple[list[JobPosting], list[JobPosting]]:
    new_jobs: list[JobPosting] = []
    existing_jobs: list[JobPosting] = []
    seen_source_ids: set[tuple[str, str]] = set()
    seen_urls: set[str] = set()
    seen_fingerprints: set[tuple[str, str, str]] = set()

    for job in jobs:
        external_id = job.external_id.strip()
        job_url = str(job.url)
        fingerprint = job.deduplication_fingerprint()
        has_seen_source_id = bool(external_id) and (job.source, external_id) in seen_source_ids
        has_seen_fingerprint = fingerprint is not None and fingerprint in seen_fingerprints

        if has_seen_source_id or job_url in seen_urls or has_seen_fingerprint:
            existing_jobs.append(job)
            continue

        if external_id:
            seen_source_ids.add((job.source, external_id))
        seen_urls.add(job_url)
        if fingerprint is not None:
            seen_fingerprints.add(fingerprint)

        if repository.job_exists(job):
            existing_jobs.append(job)
        else:
            new_jobs.append(job)

    return new_jobs, existing_jobs
