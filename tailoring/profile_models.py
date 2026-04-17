from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DEFAULT_MASTER_RESUME_PDF_PATH = Path("data/resumes/master_resume.pdf")
DEFAULT_MASTER_RESUME_JSON_PATH = Path("data/resumes/master_resume.json")


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


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileMetadata(ProfileModel):
    source_pdf: str | None = None
    parser: str | None = None
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    page_count: int | None = None
    extraction_warnings: list[str] = Field(default_factory=list)
    build_notes: list[str] = Field(default_factory=list)

    @field_validator("extraction_warnings", "build_notes", mode="before")
    @classmethod
    def _validate_messages(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class ResumeBasics(ProfileModel):
    full_name: str = ""
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None


class ResumeSummary(ProfileModel):
    base: str = ""
    highlights: list[str] = Field(default_factory=list)

    @field_validator("highlights", mode="before")
    @classmethod
    def _validate_highlights(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class SkillCategory(ProfileModel):
    category: str
    items: list[str] = Field(default_factory=list)

    @field_validator("items", mode="before")
    @classmethod
    def _validate_items(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class ExperienceEntry(ProfileModel):
    id: str
    role: str
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    current: bool = False
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @field_validator("bullets", "technologies", mode="before")
    @classmethod
    def _validate_lists(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class ProjectEntry(ProfileModel):
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


class EducationEntry(ProfileModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    details: list[str] = Field(default_factory=list)

    @field_validator("details", mode="before")
    @classmethod
    def _validate_details(cls, value: object) -> list[str]:
        return _normalize_string_list(value)


class CertificationEntry(ProfileModel):
    name: str
    issuer: str | None = None
    issue_date: str | None = None
    expires_at: str | None = None
    credential_id: str | None = None
    credential_url: str | None = None


class LanguageEntry(ProfileModel):
    language: str
    proficiency: str


class MasterResumeProfile(ProfileModel):
    metadata: ProfileMetadata = Field(default_factory=ProfileMetadata)
    basics: ResumeBasics = Field(default_factory=ResumeBasics)
    summary: ResumeSummary = Field(default_factory=ResumeSummary)
    skills: list[SkillCategory] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)


def load_master_profile(
    path: str | Path = DEFAULT_MASTER_RESUME_JSON_PATH,
) -> MasterResumeProfile:
    profile_path = Path(path)
    if not profile_path.exists():
        raise ValueError(
            f"Master profile file not found: {profile_path}. "
            "Run `python -m tailoring.build_master_profile` first."
        )

    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in master profile file: {profile_path} ({exc})") from exc

    try:
        return MasterResumeProfile.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(
            f"Master profile validation failed for {profile_path}: {exc}"
        ) from exc


def save_master_profile(
    profile: MasterResumeProfile,
    path: str | Path = DEFAULT_MASTER_RESUME_JSON_PATH,
) -> Path:
    profile_path = Path(path)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(profile.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return profile_path
