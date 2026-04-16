from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DEFAULT_MASTER_RESUME_PATH = Path("data/resumes/master_resume.json")


def _normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("Expected a list of strings")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise TypeError("Expected a list of strings")
        cleaned = item.strip()
        if not cleaned:
            continue
        fingerprint = cleaned.casefold()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        normalized.append(cleaned)
    return normalized


class ResumeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResumeBasics(ResumeModel):
    full_name: str
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None


class ResumeSummary(ResumeModel):
    base: str
    highlights: list[str] = Field(default_factory=list)

    @field_validator("highlights", mode="before")
    @classmethod
    def _validate_highlights(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class SkillCategory(ResumeModel):
    category: str
    items: list[str] = Field(default_factory=list)

    @field_validator("items", mode="before")
    @classmethod
    def _validate_items(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class ExperienceEntry(ResumeModel):
    id: str
    role: str
    company: str
    location: str | None = None
    start_date: str
    end_date: str | None = None
    current: bool = False
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @field_validator("bullets", "technologies", mode="before")
    @classmethod
    def _validate_lists(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class ProjectEntry(ResumeModel):
    id: str
    name: str
    role: str | None = None
    dates: str | None = None
    description: str | None = None
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)

    @field_validator("bullets", "technologies", "links", mode="before")
    @classmethod
    def _validate_lists(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class EducationEntry(ResumeModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    details: list[str] = Field(default_factory=list)

    @field_validator("details", mode="before")
    @classmethod
    def _validate_details(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class CertificationEntry(ResumeModel):
    name: str
    issuer: str | None = None
    issue_date: str | None = None
    expires_at: str | None = None
    credential_id: str | None = None
    credential_url: str | None = None


class LanguageEntry(ResumeModel):
    language: str
    proficiency: str


class MasterResume(ResumeModel):
    basics: ResumeBasics
    summary: ResumeSummary
    skills: list[SkillCategory] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)


def load_master_resume(path: str | Path = DEFAULT_MASTER_RESUME_PATH) -> MasterResume:
    resume_path = Path(path)
    if not resume_path.exists():
        raise ValueError(
            f"Master resume file not found: {resume_path}. "
            "Create it from data/resumes/master_resume.example.json."
        )

    try:
        payload = json.loads(resume_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in master resume file: {resume_path} ({exc})") from exc

    try:
        return MasterResume.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(
            f"Master resume validation failed for {resume_path}: {exc}"
        ) from exc
