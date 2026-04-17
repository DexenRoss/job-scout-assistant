from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from core.models import JobPosting
from tailoring.profile_models import (
    ExperienceEntry,
    MasterResumeProfile,
    ProjectEntry,
    SkillCategory,
)

STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "acc",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "job",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
    "you",
    "your",
    "br",
    "div",
    "font",
    "html",
    "li",
    "nbsp",
    "ol",
    "quot",
    "requirements",
    "responsibilities",
    "role",
    "span",
    "style",
    "team",
    "type",
    "ul",
    "united",
    "states",
    "part",
    "will",
    "workplace",
}
MAX_EXPERIENCE_ITEMS = 4
MAX_PROJECT_ITEMS = 3
MAX_BULLETS_PER_ENTRY = 4
MAX_KEYWORDS = 15
MAX_SUMMARY_HIGHLIGHTS = 3


@dataclass(frozen=True)
class TailoredResumeResult:
    resume_markdown: str
    matched_skills: list[str]
    extracted_keywords: list[str]
    missing_keywords: list[str]
    prioritized_experience_ids: list[str]
    prioritized_project_ids: list[str]
    metadata: dict[str, object]


def tailor_resume_for_job(
    master_profile: MasterResumeProfile,
    job: JobPosting,
) -> TailoredResumeResult:
    job_text = _build_job_text(job)
    flattened_skills = _flatten_skill_items(master_profile.skills)
    matched_skills = [
        skill for skill in flattened_skills if _phrase_in_text(skill, job_text)
    ]
    extracted_keywords = _extract_keywords(job, matched_skills)

    prioritized_skill_categories = _prioritize_skill_categories(
        master_profile.skills,
        job_text=job_text,
        matched_skills=matched_skills,
    )
    prioritized_experience = _prioritize_experience(
        master_profile,
        job_text,
        extracted_keywords,
    )
    prioritized_projects = _prioritize_projects(
        master_profile,
        job_text,
        extracted_keywords,
    )
    tailored_summary = _build_tailored_summary(
        master_profile=master_profile,
        matched_skills=matched_skills,
        prioritized_experience=prioritized_experience,
        job=job,
    )
    prioritized_highlights = _select_summary_highlights(
        master_profile=master_profile,
        job_text=job_text,
        extracted_keywords=extracted_keywords,
    )

    matched_resume_terms = {
        _normalize_phrase(term)
        for term in matched_skills + _collect_technology_terms(master_profile)
        if _phrase_in_text(term, job_text)
    }
    missing_keywords = [
        keyword
        for keyword in extracted_keywords
        if _normalize_phrase(keyword) not in matched_resume_terms
    ][:8]

    resume_markdown = _render_resume_markdown(
        master_profile=master_profile,
        skill_categories=prioritized_skill_categories,
        prioritized_experience=prioritized_experience,
        prioritized_projects=prioritized_projects,
        tailored_summary=tailored_summary,
        prioritized_highlights=prioritized_highlights,
    )

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "job": {
            "id": job.id,
            "source": job.source,
            "external_id": job.external_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": str(job.url),
            "score": job.score,
            "score_label": job.score_label,
            "normalized_tags": job.normalized_tags,
        },
        "keyword_signals": {
            "extracted_keywords": extracted_keywords,
            "matched_skills": matched_skills,
            "missing_keywords": missing_keywords,
        },
        "prioritized_sections": {
            "skill_categories": [category.category for category in prioritized_skill_categories],
            "experience_ids": [entry.id for entry in prioritized_experience],
            "project_ids": [project.id for project in prioritized_projects],
        },
        "constraints": {
            "honesty_policy": (
                "Only reordered, emphasized, or lightly reformulated content already present "
                "in the master profile. No new experience, skills, or achievements were added."
            )
        },
    }

    return TailoredResumeResult(
        resume_markdown=resume_markdown,
        matched_skills=matched_skills,
        extracted_keywords=extracted_keywords,
        missing_keywords=missing_keywords,
        prioritized_experience_ids=[entry.id for entry in prioritized_experience],
        prioritized_project_ids=[project.id for project in prioritized_projects],
        metadata=metadata,
    )


def _prioritize_skill_categories(
    categories: list[SkillCategory],
    *,
    job_text: str,
    matched_skills: list[str],
) -> list[SkillCategory]:
    matched_lookup = {_normalize_phrase(skill) for skill in matched_skills}
    ranked_categories: list[tuple[int, int, SkillCategory]] = []

    for index, category in enumerate(categories):
        ordered_items = sorted(
            category.items,
            key=lambda item: (
                _normalize_phrase(item) not in matched_lookup,
                item.lower(),
            ),
        )
        category_score = sum(
            1 for item in ordered_items if _normalize_phrase(item) in matched_lookup
        )
        if category_score == 0:
            category_score = sum(
                1 for item in ordered_items if _phrase_in_text(item, job_text)
            )

        ranked_categories.append(
            (
                -category_score,
                index,
                category.model_copy(update={"items": ordered_items}),
            )
        )

    ranked_categories.sort(key=lambda item: (item[0], item[1]))
    return [category for _, _, category in ranked_categories]


def _prioritize_experience(
    master_profile: MasterResumeProfile,
    job_text: str,
    extracted_keywords: list[str],
) -> list[ExperienceEntry]:
    ranked_entries = [
        (
            -_score_experience_entry(entry, job_text, extracted_keywords),
            index,
            _trim_experience_entry(entry, job_text, extracted_keywords),
        )
        for index, entry in enumerate(master_profile.experience)
    ]
    ranked_entries.sort(key=lambda item: (item[0], item[1]))
    return [entry for _, _, entry in ranked_entries[:MAX_EXPERIENCE_ITEMS]]


def _prioritize_projects(
    master_profile: MasterResumeProfile,
    job_text: str,
    extracted_keywords: list[str],
) -> list[ProjectEntry]:
    ranked_entries = [
        (
            -_score_project_entry(project, job_text, extracted_keywords),
            index,
            _trim_project_entry(project, job_text, extracted_keywords),
        )
        for index, project in enumerate(master_profile.projects)
    ]
    ranked_entries.sort(key=lambda item: (item[0], item[1]))
    return [entry for _, _, entry in ranked_entries[:MAX_PROJECT_ITEMS]]


def _build_tailored_summary(
    *,
    master_profile: MasterResumeProfile,
    matched_skills: list[str],
    prioritized_experience: list[ExperienceEntry],
    job: JobPosting,
) -> str:
    parts: list[str] = []
    base_summary = master_profile.summary.base.strip()
    if base_summary:
        parts.append(base_summary.rstrip(".") + ".")
    elif master_profile.basics.headline:
        parts.append(master_profile.basics.headline.rstrip(".") + ".")

    top_skills = matched_skills[:4]
    if top_skills:
        parts.append(
            f"Relevant strengths already evidenced in this profile include {', '.join(top_skills)}."
        )

    top_roles = [
        " at ".join(part for part in [entry.role, entry.company] if part)
        for entry in prioritized_experience[:2]
    ]
    if top_roles:
        parts.append(
            f"Most relevant prior experience for roles like {job.title} includes {', '.join(top_roles)}."
        )

    return " ".join(parts).strip()


def _select_summary_highlights(
    *,
    master_profile: MasterResumeProfile,
    job_text: str,
    extracted_keywords: list[str],
) -> list[str]:
    return _rank_text_fragments(
        master_profile.summary.highlights,
        job_text=job_text,
        extracted_keywords=extracted_keywords,
        max_items=MAX_SUMMARY_HIGHLIGHTS,
    )


def _render_resume_markdown(
    *,
    master_profile: MasterResumeProfile,
    skill_categories: list[SkillCategory],
    prioritized_experience: list[ExperienceEntry],
    prioritized_projects: list[ProjectEntry],
    tailored_summary: str,
    prioritized_highlights: list[str],
) -> str:
    lines: list[str] = []
    basics = master_profile.basics

    if basics.full_name:
        lines.append(f"# {basics.full_name}")
    if basics.headline:
        lines.append(basics.headline)
    if basics.full_name or basics.headline:
        lines.append("")

    contact_parts = [
        basics.email,
        basics.phone,
        basics.location,
        basics.linkedin,
        basics.github,
        basics.website,
    ]
    visible_contact_parts = [part for part in contact_parts if part]
    if visible_contact_parts:
        lines.append(" | ".join(visible_contact_parts))
        lines.append("")

    if tailored_summary:
        lines.append("## Professional Summary")
        lines.append(tailored_summary)
        lines.append("")

    if prioritized_highlights:
        for highlight in prioritized_highlights:
            lines.append(f"- {highlight}")
        lines.append("")

    if skill_categories:
        lines.append("## Skills")
        for category in skill_categories:
            if not category.items:
                continue
            lines.append(f"### {category.category}")
            lines.append(", ".join(category.items))
            lines.append("")

    if prioritized_experience:
        lines.append("## Experience")
        for entry in prioritized_experience:
            title_line = " | ".join(part for part in [entry.role, entry.company] if part)
            lines.append(f"### {title_line or entry.id}")
            date_range = _format_date_range(entry.start_date, entry.end_date, entry.current)
            meta_parts = [entry.location, date_range]
            visible_meta = [part for part in meta_parts if part]
            if visible_meta:
                lines.append(" | ".join(visible_meta))
            if entry.technologies:
                lines.append(f"Technologies: {', '.join(entry.technologies)}")
            for bullet in entry.bullets:
                lines.append(f"- {bullet}")
            lines.append("")

    if prioritized_projects:
        lines.append("## Projects")
        for project in prioritized_projects:
            lines.append(f"### {project.name}")
            meta_parts = [project.role, project.dates]
            visible_meta = [part for part in meta_parts if part]
            if visible_meta:
                lines.append(" | ".join(visible_meta))
            if project.description:
                lines.append(project.description)
            if project.technologies:
                lines.append(f"Technologies: {', '.join(project.technologies)}")
            if project.links:
                lines.append(f"Links: {', '.join(project.links)}")
            for bullet in project.bullets:
                lines.append(f"- {bullet}")
            lines.append("")

    if master_profile.education:
        lines.append("## Education")
        for entry in master_profile.education:
            lines.append(f"### {entry.institution}")
            if entry.degree:
                degree_line = entry.degree
                if entry.field_of_study:
                    degree_line = f"{degree_line}, {entry.field_of_study}"
                lines.append(degree_line)
            date_parts = [entry.start_date, entry.end_date]
            visible_dates = [part for part in date_parts if part]
            if visible_dates:
                lines.append(" - ".join(visible_dates))
            for detail in entry.details:
                lines.append(f"- {detail}")
            lines.append("")

    if master_profile.certifications:
        lines.append("## Certifications")
        for certification in master_profile.certifications:
            detail_parts = [certification.issuer, certification.issue_date]
            visible_details = [part for part in detail_parts if part]
            detail_text = f" ({' | '.join(visible_details)})" if visible_details else ""
            lines.append(f"- {certification.name}{detail_text}")
        lines.append("")

    if master_profile.languages:
        lines.append("## Languages")
        for language in master_profile.languages:
            lines.append(f"- {language.language}: {language.proficiency}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _score_experience_entry(
    entry: ExperienceEntry,
    job_text: str,
    extracted_keywords: list[str],
) -> int:
    entry_text = _normalize_phrase(
        " ".join(
            [
                entry.role,
                entry.company or "",
                entry.location or "",
                " ".join(entry.technologies),
                " ".join(entry.bullets),
            ]
        )
    )

    score = 0
    for keyword in extracted_keywords:
        if _phrase_in_text(keyword, entry_text):
            score += 5 if " " in keyword else 3
    for technology in entry.technologies:
        if _phrase_in_text(technology, job_text):
            score += 6
    if entry.current:
        score += 1
    return score


def _score_project_entry(
    project: ProjectEntry,
    job_text: str,
    extracted_keywords: list[str],
) -> int:
    project_text = _normalize_phrase(
        " ".join(
            [
                project.name,
                project.role or "",
                project.description or "",
                " ".join(project.technologies),
                " ".join(project.bullets),
            ]
        )
    )

    score = 0
    for keyword in extracted_keywords:
        if _phrase_in_text(keyword, project_text):
            score += 5 if " " in keyword else 3
    for technology in project.technologies:
        if _phrase_in_text(technology, job_text):
            score += 6
    return score


def _trim_experience_entry(
    entry: ExperienceEntry,
    job_text: str,
    extracted_keywords: list[str],
) -> ExperienceEntry:
    return entry.model_copy(
        update={
            "bullets": _rank_text_fragments(
                entry.bullets,
                job_text=job_text,
                extracted_keywords=extracted_keywords,
                max_items=MAX_BULLETS_PER_ENTRY,
            )
        }
    )


def _trim_project_entry(
    project: ProjectEntry,
    job_text: str,
    extracted_keywords: list[str],
) -> ProjectEntry:
    return project.model_copy(
        update={
            "bullets": _rank_text_fragments(
                project.bullets,
                job_text=job_text,
                extracted_keywords=extracted_keywords,
                max_items=MAX_BULLETS_PER_ENTRY,
            )
        }
    )


def _rank_text_fragments(
    fragments: list[str],
    *,
    job_text: str,
    extracted_keywords: list[str],
    max_items: int,
) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    for index, fragment in enumerate(fragments):
        fragment_text = _normalize_phrase(fragment)
        score = 0
        for keyword in extracted_keywords:
            if _phrase_in_text(keyword, fragment_text):
                score += 4 if " " in keyword else 2
        if _normalize_phrase(fragment) and _normalize_phrase(fragment) in job_text:
            score += 1
        ranked.append((-score, index, fragment))

    ranked.sort(key=lambda item: (item[0], item[1]))
    return [fragment for _, _, fragment in ranked[:max_items]]


def _extract_keywords(job: JobPosting, matched_skills: list[str]) -> list[str]:
    keyword_scores: dict[str, int] = {}
    cleaned_description = _clean_text(job.description or "")
    title_tokens = _tokenize(job.title)

    for skill in matched_skills:
        normalized = _normalize_phrase(skill)
        if _is_useful_keyword(normalized):
            keyword_scores[normalized] = keyword_scores.get(normalized, 0) + 10

    for tag in job.normalized_tags:
        normalized = _normalize_phrase(tag)
        if _is_useful_keyword(normalized):
            keyword_scores[normalized] = keyword_scores.get(normalized, 0) + 8

    for phrase in _build_keyword_phrases(title_tokens):
        if _is_useful_keyword(phrase):
            keyword_scores[phrase] = keyword_scores.get(phrase, 0) + 7

    for token in title_tokens:
        if _is_useful_keyword(token):
            keyword_scores[token] = keyword_scores.get(token, 0) + 6

    for token in _tokenize(cleaned_description):
        if _is_useful_keyword(token):
            keyword_scores[token] = keyword_scores.get(token, 0) + 1

    ranked_keywords = sorted(
        keyword_scores.items(),
        key=lambda item: (-item[1], -len(item[0].split()), item[0]),
    )
    return [keyword for keyword, _ in ranked_keywords[:MAX_KEYWORDS]]


def _flatten_skill_items(categories: list[SkillCategory]) -> list[str]:
    flattened: list[str] = []
    seen: set[str] = set()
    for category in categories:
        for item in category.items:
            fingerprint = item.casefold()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            flattened.append(item)
    return flattened


def _collect_technology_terms(master_profile: MasterResumeProfile) -> list[str]:
    terms: list[str] = []
    for experience in master_profile.experience:
        terms.extend(experience.technologies)
    for project in master_profile.projects:
        terms.extend(project.technologies)
    return terms


def _build_job_text(job: JobPosting) -> str:
    return _normalize_phrase(
        " ".join(
            [
                job.title,
                job.company,
                job.location or "",
                _clean_text(job.description or ""),
                " ".join(job.normalized_tags),
            ]
        )
    )


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9\+\#\.-]{1,}", _normalize_phrase(text))
    return [
        token
        for token in tokens
        if token not in STOPWORDS and len(token) >= 3
    ]


def _build_keyword_phrases(tokens: list[str]) -> list[str]:
    phrases: list[str] = []
    seen: set[str] = set()
    for left, right in zip(tokens, tokens[1:]):
        phrase = f"{left} {right}"
        if phrase in seen:
            continue
        seen.add(phrase)
        phrases.append(phrase)
    return phrases[:6]


def _is_useful_keyword(keyword: str) -> bool:
    if not keyword or keyword.isdigit():
        return False

    parts = [part for part in keyword.split() if part]
    if not parts:
        return False

    if len(parts) == 1:
        return len(parts[0]) >= 3 and parts[0] not in STOPWORDS

    meaningful_parts = [
        part for part in parts if part not in STOPWORDS and not part.isdigit() and len(part) >= 2
    ]
    return len(meaningful_parts) > 0


def _phrase_in_text(phrase: str, text: str) -> bool:
    normalized_phrase = _normalize_phrase(phrase)
    normalized_text = _normalize_phrase(text)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_text} "


def _clean_text(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", html.unescape(text))
    return re.sub(r"\s+", " ", without_tags).strip()


def _normalize_phrase(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9\+\#\.]+", " ", _clean_text(text).lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _format_date_range(
    start_date: str | None,
    end_date: str | None,
    current: bool,
) -> str | None:
    if not start_date and not end_date:
        return None
    if start_date and current:
        return f"{start_date} - Present"
    if start_date and end_date:
        return f"{start_date} - {end_date}"
    return start_date or end_date
