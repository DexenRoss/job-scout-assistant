from __future__ import annotations

from dataclasses import dataclass

from core.models import JobPosting

REMOTE_KEYWORDS = ("remote", "remoto", "anywhere", "worldwide", "distributed")
ONSITE_KEYWORDS = ("on-site", "onsite", "hybrid", "in office", "office-based")
CONTRACT_KEYWORDS = ("contract", "contractor", "temporary", "temp", "freelance")
SENIORITY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "intern": ("intern", "internship", "trainee"),
    "junior": ("junior", "jr", "entry level", "entry-level", "associate"),
    "mid": ("mid", "mid-level", "intermediate"),
    "senior": ("senior", "sr", "staff", "lead", "principal"),
}


@dataclass(frozen=True)
class JobScorer:
    enabled: bool
    min_notify_score: int
    preferred_keywords: list[str]
    preferred_locations: list[str]
    seniority_preference: str | None
    exclude_keywords: list[str]

    def score(self, job: JobPosting) -> JobPosting:
        if not self.enabled:
            job.score = None
            job.score_label = None
            job.score_reasons = []
            return job

        score = 50
        reasons: list[str] = []

        preferred_keyword_points, keyword_reasons = self._score_preferred_keywords(job)
        score += preferred_keyword_points
        reasons.extend(keyword_reasons)

        location_points, location_reasons = self._score_location(job)
        score += location_points
        reasons.extend(location_reasons)

        seniority_points, seniority_reasons = self._score_seniority(job)
        score += seniority_points
        reasons.extend(seniority_reasons)

        negative_points, negative_reasons = self._score_negative_signals(job)
        score += negative_points
        reasons.extend(negative_reasons)

        if not job.is_relevant:
            score = min(score - 30, 40)
            reasons.append(f"Filtered out before notification: {job.relevance_reason or 'not relevant'}")

        score = max(0, min(100, score))
        job.score = score
        job.score_label = self._label_for_score(score)
        job.score_reasons = reasons[:5] if reasons else ["No strong preference signals detected"]
        return job

    def should_notify(self, job: JobPosting) -> bool:
        if not job.is_relevant:
            return False
        if not self.enabled:
            return True
        return (job.score or 0) >= self.min_notify_score

    def _score_preferred_keywords(self, job: JobPosting) -> tuple[int, list[str]]:
        if not self.preferred_keywords:
            return 0, []

        texts = self._field_texts(job)
        points = 0
        reasons: list[str] = []

        for keyword in self.preferred_keywords:
            if not keyword:
                continue
            if keyword in texts["title"]:
                points += 12
                reasons.append(f"Preferred keyword in title: {keyword}")
            elif keyword in texts["tags"]:
                points += 8
                reasons.append(f"Preferred keyword in tags: {keyword}")
            elif keyword in texts["description"]:
                points += 6
                reasons.append(f"Preferred keyword in description: {keyword}")
            elif keyword in texts["company"]:
                points += 4
                reasons.append(f"Preferred keyword in company: {keyword}")

        return min(points, 30), reasons

    def _score_location(self, job: JobPosting) -> tuple[int, list[str]]:
        location_text = " ".join(
            part.lower()
            for part in [
                job.location or "",
                job.raw_location or "",
                job.title,
                job.description or "",
                " ".join(job.normalized_tags),
            ]
            if part
        )
        points = 0
        reasons: list[str] = []

        matched_locations = [
            location
            for location in self.preferred_locations
            if location and location in location_text
        ]
        if matched_locations:
            points += min(24, 18 + (len(matched_locations) - 1) * 3)
            reasons.append(f"Preferred location match: {matched_locations[0]}")

        if any(keyword in location_text for keyword in REMOTE_KEYWORDS):
            points += 10
            reasons.append("Remote-friendly location")
        elif self._prefers_remote() and any(keyword in location_text for keyword in ONSITE_KEYWORDS):
            points -= 12
            reasons.append("On-site or hybrid role conflicts with remote preference")
        elif self.preferred_locations and not matched_locations:
            points -= 8
            reasons.append("Location does not match preferred locations")

        return points, reasons

    def _score_seniority(self, job: JobPosting) -> tuple[int, list[str]]:
        if not self.seniority_preference:
            return 0, []

        seniority_text = " ".join(
            part.lower()
            for part in [
                job.title,
                job.seniority or "",
                " ".join(job.normalized_tags),
            ]
            if part
        )
        preferred_group = self._resolve_seniority_group(self.seniority_preference)

        if self._matches_seniority_group(seniority_text, preferred_group):
            return 15, [f"Seniority matches preference: {self.seniority_preference}"]

        if preferred_group != "unknown":
            for group_name, keywords in SENIORITY_KEYWORDS.items():
                if group_name == preferred_group:
                    continue
                if any(keyword in seniority_text for keyword in keywords):
                    return -12, [f"Seniority conflicts with preference: {self.seniority_preference}"]

        return 0, []

    def _score_negative_signals(self, job: JobPosting) -> tuple[int, list[str]]:
        haystack = self._build_search_text(job)
        points = 0
        reasons: list[str] = []

        matched_excluded = [
            keyword for keyword in self.exclude_keywords if keyword and keyword in haystack
        ]
        if matched_excluded:
            points -= 25
            reasons.append(f"Negative keyword signal: {matched_excluded[0]}")

        if any(keyword in haystack for keyword in CONTRACT_KEYWORDS):
            points -= 8
            reasons.append("Contractor or temporary signal")

        return points, reasons

    @staticmethod
    def _build_search_text(job: JobPosting) -> str:
        return " ".join(JobScorer._field_texts(job).values())

    @staticmethod
    def _field_texts(job: JobPosting) -> dict[str, str]:
        return {
            "title": job.title.lower(),
            "description": (job.description or "").lower(),
            "company": job.company.lower(),
            "location": (job.location or "").lower(),
            "tags": " ".join(job.normalized_tags).lower(),
        }

    def _prefers_remote(self) -> bool:
        return any(
            any(keyword in location for keyword in REMOTE_KEYWORDS)
            for location in self.preferred_locations
        )

    @staticmethod
    def _label_for_score(score: int) -> str:
        if score >= 80:
            return "strong_match"
        if score >= 65:
            return "good_match"
        if score >= 45:
            return "weak_match"
        return "poor_match"

    def _resolve_seniority_group(self, preference: str) -> str:
        lowered = preference.lower()
        for group_name, keywords in SENIORITY_KEYWORDS.items():
            if lowered == group_name or lowered in keywords:
                return group_name
        return "unknown"

    @staticmethod
    def _matches_seniority_group(text: str, group_name: str) -> bool:
        if group_name == "unknown":
            return False
        return any(keyword in text for keyword in SENIORITY_KEYWORDS[group_name])
