from __future__ import annotations

import requests

from core.logger import get_logger
from core.models import JobPosting
from notifications.templates import build_discord_message

logger = get_logger(__name__)


class DiscordNotifier:
    def __init__(self, webhook_url: str | None, timeout_seconds: float = 10.0) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def send_job_alert(self, job: JobPosting) -> bool:
        if not self.webhook_url:
            logger.warning("Discord webhook is not configured; skipping notification")
            return False

        payload = build_discord_message(job)

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            logger.info("Discord notification sent for job '%s'", job.title)
            return True
        except Exception as exc:
            logger.exception(
                "Failed to send Discord notification for job '%s': %s",
                job.title,
                exc,
            )
            return False