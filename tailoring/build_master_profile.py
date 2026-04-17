from __future__ import annotations

import re
from argparse import ArgumentParser
from pathlib import Path

from tailoring.parse_resume_pdf import extract_text_from_pdf
from tailoring.profile_models import (
    DEFAULT_MASTER_RESUME_JSON_PATH,
    DEFAULT_MASTER_RESUME_PDF_PATH,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    MasterResumeProfile,
    ProfileMetadata,
    ProjectEntry,
    ResumeBasics,
    ResumeSummary,
    SkillCategory,
    save_master_profile,
)

SECTION_ALIASES = {
    "summary": {"summary", "professional summary", "profile", "about", "overview"},
    "skills": {"skills", "technical skills", "core skills", "technologies", "tech stack"},
    "experience": {
        "experience",
        "professional experience",
        "work experience",
        "employment",
    },
    "projects": {"projects", "selected projects", "personal projects"},
    "education": {"education", "academic background"},
    "certifications": {"certifications", "certificates", "licenses"},
    "languages": {"languages", "language skills"},
    "additional_information": {"additional information", "additional info"},
}
CONTACT_LABELS = {
    "linkedin": re.compile(r"linkedin\.com", re.I),
    "github": re.compile(r"github\.com", re.I),
}
EMAIL_PATTERN = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
PHONE_PATTERN = re.compile(
    r"(\+\d[\d\s().-]{7,}\d|\b\d{10,}\b|\b\d{2,4}[\s.-]\d{2,4}[\s.-]\d{2,6}\b)"
)
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.I)
DATE_RANGE_PATTERN = re.compile(
    r"(?P<start>\d{4}(?:-\d{2})?|(?:[A-Za-z]{3,9}\s+)?\d{4})"
    r"(?:\s*(?:-|–|to)\s*"
    r"(?P<end>present|current|now|\d{4}(?:-\d{2})?|(?:[A-Za-z]{3,9}\s+)?\d{4}))?",
    re.I,
)


def build_master_profile_from_pdf(
    pdf_path: str | Path = DEFAULT_MASTER_RESUME_PDF_PATH,
) -> MasterResumeProfile:
    extraction = extract_text_from_pdf(pdf_path)
    lines = _split_lines(extraction.text)
    preamble, sections = _split_sections(lines)
    basics, remaining_preamble = _parse_basics(
        preamble,
        sections.get("additional_information", []),
    )

    summary_section = sections.get("summary", [])
    summary = _parse_summary(summary_section, remaining_preamble)
    skills = _parse_skills(sections.get("skills", []))
    experience = _parse_experience(sections.get("experience", []))
    projects = _parse_projects(sections.get("projects", []))
    education = _parse_education(sections.get("education", []))
    certifications = _parse_certifications(sections.get("certifications", []))
    languages = _parse_languages(sections.get("languages", []))

    build_notes: list[str] = []
    if not experience:
        build_notes.append(
            "No clear experience blocks were detected. Review `master_resume.json` manually."
        )
    if not skills:
        build_notes.append(
            "No structured skills section was detected. Add or refine skills manually if needed."
        )
    if not summary.base and remaining_preamble:
        build_notes.append(
            "A formal summary section was not detected. The profile summary was inferred conservatively."
        )

    return MasterResumeProfile(
        metadata=ProfileMetadata(
            source_pdf=str(Path(pdf_path)),
            parser=extraction.parser,
            page_count=extraction.page_count,
            extraction_warnings=extraction.warnings,
            build_notes=build_notes,
        ),
        basics=basics,
        summary=summary,
        skills=skills,
        experience=experience,
        projects=projects,
        education=education,
        certifications=certifications,
        languages=languages,
    )


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Extract a structured master resume profile from a PDF.",
    )
    parser.add_argument(
        "--input-pdf",
        default=str(DEFAULT_MASTER_RESUME_PDF_PATH),
        help="Path to the source resume PDF.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_MASTER_RESUME_JSON_PATH),
        help="Path where the structured master profile JSON will be written.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    profile = build_master_profile_from_pdf(args.input_pdf)
    output_path = save_master_profile(profile, args.output_json)
    print(f"Master profile written to: {output_path}")
    if profile.metadata.extraction_warnings:
        print("Extraction warnings:")
        for warning in profile.metadata.extraction_warnings:
            print(f"- {warning}")
    if profile.metadata.build_notes:
        print("Build notes:")
        for note in profile.metadata.build_notes:
            print(f"- {note}")


def _split_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    normalized: list[str] = []
    for line in lines:
        clean_line = re.sub(r"\s+", " ", line).strip()
        normalized.append(clean_line)
    return normalized


def _split_sections(lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    preamble: list[str] = []
    sections: dict[str, list[str]] = {key: [] for key in SECTION_ALIASES}
    current_section: str | None = None

    for line in lines:
        heading = _canonical_section_heading(line)
        if heading:
            current_section = heading
            continue

        if current_section is None:
            preamble.append(line)
        else:
            sections[current_section].append(line)

    return preamble, sections


def _canonical_section_heading(line: str) -> str | None:
    normalized = re.sub(r"[^a-zA-Z ]+", " ", line).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    for section_name, aliases in SECTION_ALIASES.items():
        if normalized in aliases:
            return section_name
    return None


def _parse_basics(
    preamble: list[str],
    additional_information_lines: list[str],
) -> tuple[ResumeBasics, list[str]]:
    non_empty = [line for line in preamble if line]
    if not non_empty:
        return ResumeBasics(), []

    full_name = non_empty[0]
    remaining = non_empty[1:]
    headline: str | None = None
    summary_seed: list[str] = []
    basics = ResumeBasics(full_name=full_name)

    for line in remaining:
        residual = line

        email_match = EMAIL_PATTERN.search(line)
        if email_match and basics.email is None:
            basics.email = email_match.group(0)
            residual = residual.replace(email_match.group(0), " ")

        phone_match = PHONE_PATTERN.search(line)
        if phone_match and basics.phone is None:
            basics.phone = phone_match.group(0).strip()
            residual = residual.replace(phone_match.group(0), " ")

        for url in URL_PATTERN.findall(line):
            if CONTACT_LABELS["linkedin"].search(url) and basics.linkedin is None:
                basics.linkedin = url
            elif CONTACT_LABELS["github"].search(url) and basics.github is None:
                basics.github = url
            elif basics.website is None:
                basics.website = url
            residual = residual.replace(url, " ")

        residual = re.sub(r"[|•]+", " ", residual)
        residual = re.sub(r"\s+", " ", residual).strip(" ,|-")
        if not residual:
            continue

        if headline is None and len(residual.split()) <= 14 and not any(
            character.isdigit() for character in residual
        ):
            headline = residual
            continue
        if basics.location is None and len(residual.split()) <= 8:
            basics.location = residual
            continue
        summary_seed.append(residual)

    basics.headline = headline
    _apply_additional_information_to_basics(basics, additional_information_lines)
    return basics, summary_seed


def _parse_summary(summary_lines: list[str], fallback_lines: list[str]) -> ResumeSummary:
    raw_lines = [line for line in summary_lines if line] or [line for line in fallback_lines if line]
    if not raw_lines:
        return ResumeSummary()

    bullet_lines = [line.lstrip("- ").strip() for line in raw_lines if line.startswith("-")]
    prose_lines = [line for line in raw_lines if not line.startswith("-")]

    if not prose_lines and bullet_lines:
        prose_lines = bullet_lines[:1]
        bullet_lines = bullet_lines[1:]

    return ResumeSummary(
        base=" ".join(prose_lines[:3]).strip(),
        highlights=bullet_lines[:5],
    )


def _parse_skills(lines: list[str]) -> list[SkillCategory]:
    skill_categories: list[SkillCategory] = []
    generic_items: list[str] = []
    current_category: str | None = None

    for line in lines:
        if not line:
            continue
        if ":" in line:
            category, raw_items = line.split(":", 1)
            items = _split_csv_items(raw_items)
            if items:
                cleaned_category = category.strip().lstrip("- ")
                skill_categories.append(
                    SkillCategory(category=cleaned_category, items=items)
                )
                current_category = cleaned_category
            continue

        if line.lower().endswith("skills"):
            current_category = line.strip().lstrip("- ")
            continue
        if current_category and skill_categories:
            skill_categories[-1] = skill_categories[-1].model_copy(
                update={
                    "items": skill_categories[-1].items + _split_csv_items(line)
                }
            )
            continue
        generic_items.extend(_split_csv_items(line))

    if generic_items:
        skill_categories.append(SkillCategory(category="General", items=generic_items))
    return skill_categories


def _parse_experience(lines: list[str]) -> list[ExperienceEntry]:
    return [
        _build_experience_entry(block, index)
        for index, block in enumerate(_split_experience_blocks(_preclean_experience_lines(lines)), start=1)
        if block
    ]


def _parse_projects(lines: list[str]) -> list[ProjectEntry]:
    projects: list[ProjectEntry] = []
    for index, block in enumerate(_split_blocks(lines), start=1):
        if not block:
            continue

        name = block[0]
        role: str | None = None
        dates: str | None = None
        description_lines: list[str] = []
        bullets: list[str] = []
        technologies: list[str] = []
        links: list[str] = []

        for line in block[1:]:
            lower_line = line.lower()
            if lower_line.startswith(("technologies:", "tech stack:", "stack:", "tools:")):
                technologies.extend(_split_csv_items(line.split(":", 1)[1]))
                continue
            if URL_PATTERN.search(line):
                links.append(URL_PATTERN.search(line).group(0))
                continue
            if DATE_RANGE_PATTERN.search(line) and dates is None:
                dates = line
                continue
            if line.startswith("-"):
                bullets.append(line.lstrip("- ").strip())
                continue
            if role is None and len(line.split()) <= 12:
                role = line
                continue
            description_lines.append(line)

        projects.append(
            ProjectEntry(
                id=f"project_{index}",
                name=name,
                role=role,
                dates=dates,
                description=" ".join(description_lines[:2]).strip() or None,
                bullets=bullets,
                technologies=technologies,
                links=links,
            )
        )

    return projects


def _parse_education(lines: list[str]) -> list[EducationEntry]:
    education: list[EducationEntry] = []
    for block in _split_education_blocks(_preclean_education_lines(lines)):
        if not block:
            continue

        title_line = block[0]
        institution = block[1] if len(block) > 1 else block[0]
        degree = re.sub(r"\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\b.*$", "", title_line).strip()
        if degree == institution:
            degree = None
        details = [
            line.lstrip("- ").strip()
            for line in block[2:]
            if line and not DATE_RANGE_PATTERN.fullmatch(line)
        ]
        start_date, end_date = _extract_dates_from_lines(block)
        education.append(
            EducationEntry(
                institution=institution,
                degree=degree,
                start_date=start_date,
                end_date=end_date,
                details=details,
            )
        )
    return [
        entry
        for entry in education
        if not (
            (entry.degree or "").lower().startswith("anticipated graduation date")
            or (entry.institution or "").lower().startswith("relevant coursework:")
        )
    ]


def _parse_certifications(lines: list[str]) -> list[CertificationEntry]:
    certifications: list[CertificationEntry] = []
    for line in lines:
        if not line:
            continue
        parts = [part.strip() for part in re.split(r"\s+\|\s+|\s+-\s+", line) if part.strip()]
        if not parts:
            continue
        certifications.append(
            CertificationEntry(
                name=parts[0],
                issuer=parts[1] if len(parts) > 1 else None,
                issue_date=parts[2] if len(parts) > 2 else None,
            )
        )
    return certifications


def _parse_languages(lines: list[str]) -> list[LanguageEntry]:
    languages: list[LanguageEntry] = []
    for line in lines:
        if not line:
            continue
        normalized_line = line.lstrip("- ").strip()
        if "linkedin" in normalized_line.lower() or "github" in normalized_line.lower():
            continue
        parts = [part.strip() for part in re.split(r"\s+[—–-]\s+|:|\|", normalized_line, maxsplit=1) if part.strip()]
        if len(parts) == 2:
            languages.append(LanguageEntry(language=parts[0], proficiency=parts[1]))
    return languages


def _build_experience_entry(block: list[str], index: int) -> ExperienceEntry:
    header = block[0]
    role, company, start_date, end_date = _parse_experience_header(header)
    if start_date is None:
        start_date, end_date = _extract_dates_from_lines(block[1:])
    current = bool(end_date and end_date.lower() in {"present", "current", "now"})
    location = _extract_location(block[1:]) or _extract_location([header])
    header_without_dates = DATE_RANGE_PATTERN.sub("", header).strip(" |-–,")
    if location and location in {header_without_dates, role, company or ""}:
        location = None
    bullets: list[str] = []
    technologies: list[str] = []

    for line in block[1:]:
        lower_line = line.lower()
        if lower_line.startswith(("technologies:", "tech stack:", "stack:", "tools:")):
            technologies.extend(_split_csv_items(line.split(":", 1)[1]))
            continue
        if line.startswith("-"):
            bullets.append(line.lstrip("- ").strip())

    return ExperienceEntry(
        id=f"experience_{index}",
        role=role,
        company=company,
        location=location,
        start_date=start_date,
        end_date=end_date,
        current=current,
        bullets=bullets,
        technologies=technologies,
    )


def _split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if not line:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)

    if current:
        blocks.append(current)

    return blocks


def _split_role_company(header: str) -> tuple[str, str | None]:
    for separator in (" at ", " | ", " - ", " @ "):
        if separator in header:
            left, right = header.split(separator, 1)
            return left.strip(), right.strip() or None
    return header.strip(), None


def _parse_experience_header(header: str) -> tuple[str, str | None, str | None, str | None]:
    start_date, end_date = _extract_dates_from_lines([header])
    clean_header = DATE_RANGE_PATTERN.sub("", header).strip(" |-–,")
    role, company = _split_role_company(clean_header)
    if company is None and "," in clean_header:
        left, right = clean_header.split(",", 1)
        role = left.strip()
        company = right.strip() or None
    return role, company, start_date, end_date


def _extract_dates_from_lines(lines: list[str]) -> tuple[str | None, str | None]:
    for line in lines:
        match = DATE_RANGE_PATTERN.search(line)
        if match:
            start = match.group("start")
            end = match.group("end")
            return start, end
    return None, None


def _extract_location(lines: list[str]) -> str | None:
    for line in lines:
        if DATE_RANGE_PATTERN.search(line):
            remainder = DATE_RANGE_PATTERN.sub("", line, count=1)
            remainder = remainder.strip(" |-–,")
            if remainder:
                return remainder
    return None


def _split_csv_items(value: str) -> list[str]:
    items = [item.strip(" -") for item in value.split(",")]
    return [item for item in items if item]


def _apply_additional_information_to_basics(
    basics: ResumeBasics,
    lines: list[str],
) -> None:
    for line in lines:
        normalized = line.strip()
        if not normalized:
            continue
        if "linkedin:" in normalized.lower() or "github:" in normalized.lower():
            linkedin_match = re.search(r"(?i)linkedin:\s*(.*?)(?=\s+github:|$)", normalized)
            github_match = re.search(r"(?i)github:\s*(.*)$", normalized)
            if linkedin_match and basics.linkedin is None:
                basics.linkedin = linkedin_match.group(1).strip()
            if github_match and basics.github is None:
                basics.github = github_match.group(1).strip()
        elif normalized.lower().startswith("linkedin:") and basics.linkedin is None:
            basics.linkedin = normalized.split(":", 1)[1].strip()
        elif normalized.lower().startswith("github:") and basics.github is None:
            basics.github = normalized.split(":", 1)[1].strip()


def _preclean_experience_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        if not line or line == "1" or line == "2":
            continue
        cleaned.append(line)
    return cleaned


def _preclean_education_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        if not line:
            continue
        cleaned.append(line)
    return cleaned


def _split_experience_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if not line:
            if current:
                blocks.append(current)
                current = []
            continue

        if current and _looks_like_experience_header(line) and _current_block_is_complete(current):
            blocks.append(current)
            current = [line]
            continue

        current.append(line)

    if current:
        blocks.append(current)

    return blocks


def _looks_like_experience_header(line: str) -> bool:
    normalized = line.lower()
    return bool(DATE_RANGE_PATTERN.search(line)) and not line.startswith("-")


def _current_block_is_complete(block: list[str]) -> bool:
    return any(item.startswith("-") for item in block) or any(
        DATE_RANGE_PATTERN.search(item) for item in block[1:]
    )


def _split_education_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if current and DATE_RANGE_PATTERN.search(line) and not line.startswith("-"):
            blocks.append(current)
            current = [line]
            continue
        current.append(line)

    if current:
        blocks.append(current)

    normalized_blocks: list[list[str]] = []
    for block in blocks:
        if block:
            normalized_blocks.append(block)
    return normalized_blocks


if __name__ == "__main__":
    main()
