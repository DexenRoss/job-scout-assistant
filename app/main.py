from __future__ import annotations

from core.config import get_settings
from core.logger import setup_logging, get_logger
from notifications.discord import DiscordNotifier
from pipeline.deduplicate_jobs import split_new_and_existing_jobs
from pipeline.discover_jobs import discover_jobs
from pipeline.filter_jobs import JobFilter
from pipeline.score_jobs import JobScorer
from storage.db import initialize_database
from storage.repositories import JobRepository


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = get_logger(__name__)

    logger.info("Starting Job Scout Assistant execution")

    initialize_database(settings.database_path)
    repository = JobRepository(settings.database_path)
    filter_service = JobFilter(
        include_keywords=settings.include_keywords,
        exclude_keywords=settings.exclude_keywords,
    )
    scorer = JobScorer(
        enabled=settings.scoring_enabled,
        min_notify_score=settings.scoring_min_notify_score,
        preferred_keywords=settings.preferred_keywords,
        preferred_locations=settings.preferred_locations,
        seniority_preference=settings.seniority_preference,
        exclude_keywords=settings.exclude_keywords,
    )
    notifier = DiscordNotifier(webhook_url=settings.discord_webhook_url)

    discovered_jobs = discover_jobs(settings)
    logger.info("Discovered %s jobs from enabled sources", len(discovered_jobs))

    new_jobs, existing_jobs = split_new_and_existing_jobs(discovered_jobs, repository)
    logger.info("Found %s new jobs and %s existing jobs", len(new_jobs), len(existing_jobs))

    relevant_jobs = []
    inserted_count = 0
    scored_count = 0
    threshold_pass_count = 0
    notification_count = 0

    for job in new_jobs:
        filtered_job = filter_service.evaluate(job)
        scored_job = scorer.score(filtered_job)
        inserted = repository.insert_job_if_not_exists(scored_job)
        if not inserted:
            logger.warning(
                "Skipped storage duplicate after deduplication for source=%s external_id=%s url=%s",
                scored_job.source,
                scored_job.external_id,
                scored_job.url,
            )
            continue

        inserted_count += 1
        if scored_job.score is not None:
            scored_count += 1

        if scored_job.is_relevant:
            relevant_jobs.append(scored_job)
            if scorer.should_notify(scored_job):
                threshold_pass_count += 1

    logger.info("Inserted %s new jobs into storage", inserted_count)
    logger.info("Marked %s jobs as relevant after filtering", len(relevant_jobs))
    logger.info("Scored %s new jobs", scored_count)
    logger.info(
        "%s relevant jobs met the notification threshold",
        threshold_pass_count,
    )

    for job in relevant_jobs:
        if not scorer.should_notify(job):
            continue

        sent = notifier.send_job_alert(job)
        if sent:
            repository.mark_as_notified(job)
            notification_count += 1

    logger.info("Sent %s Discord notifications", notification_count)
    logger.info("Job Scout Assistant execution finished")


if __name__ == "__main__":
    main()
