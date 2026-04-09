from __future__ import annotations

from core.models import JobPosting
from storage.repositories import JobRepository


def split_new_and_existing_jobs(
    jobs: list[JobPosting],
    repository: JobRepository,
) -> tuple[list[JobPosting], list[JobPosting]]:
    new_jobs: list[JobPosting] = []
    existing_jobs: list[JobPosting] = []

    for job in jobs:
        if repository.job_exists(job):
            existing_jobs.append(job)
        else:
            new_jobs.append(job)

    return new_jobs, existing_jobs