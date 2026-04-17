from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PdfExtractionResult:
    text: str
    page_count: int
    parser: str
    warnings: list[str]


def extract_text_from_pdf(pdf_path: str | Path) -> PdfExtractionResult:
    path = Path(pdf_path)
    if not path.exists():
        raise ValueError(f"Resume PDF not found: {path}")

    try:
        return _extract_with_pypdf(path)
    except ModuleNotFoundError:
        if shutil.which("pdftotext"):
            return _extract_with_pdftotext(path)
        raise ValueError(
            "PDF extraction requires `pypdf` or the `pdftotext` system command. "
            "Install dependencies with `pip install -r requirements.txt`."
        ) from None


def normalize_extracted_pdf_text(text: str) -> str:
    normalized = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u2022", "- ").replace("\uf0b7", "- ")
    normalized = re.sub(r"(?<=[A-Za-zÁÉÍÓÚÑáéíóúñ,])(?=(?:January|February|March|April|May|June|July|August|September|October|November|December)\b)", " ", normalized)
    normalized = re.sub(r"(?<=[A-Za-z])(?=\d{4}-\d{2}\b)", " ", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"(?m)^\s*\d+\s*$", "", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _extract_with_pypdf(path: Path) -> PdfExtractionResult:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    warnings: list[str] = []
    page_texts: list[str] = []

    for index, page in enumerate(reader.pages, start=1):
        extracted = page.extract_text() or ""
        if not extracted.strip():
            warnings.append(
                f"Page {index} returned little or no selectable text during extraction."
            )
        page_texts.append(extracted)

    text = normalize_extracted_pdf_text("\n\n".join(page_texts))
    if len(text) < 80:
        warnings.append(
            "Very little text was extracted from the PDF. The file may be image-based "
            "or the text layer may be incomplete."
        )

    return PdfExtractionResult(
        text=text,
        page_count=len(reader.pages),
        parser="pypdf",
        warnings=warnings,
    )


def _extract_with_pdftotext(path: Path) -> PdfExtractionResult:
    result = subprocess.run(
        ["pdftotext", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = normalize_extracted_pdf_text(result.stdout)
    warnings: list[str] = []
    if len(text) < 80:
        warnings.append(
            "Very little text was extracted from the PDF. The file may be image-based "
            "or the text layer may be incomplete."
        )

    return PdfExtractionResult(
        text=text,
        page_count=0,
        parser="pdftotext",
        warnings=warnings,
    )
