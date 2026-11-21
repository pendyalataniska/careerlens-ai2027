from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

import pymupdf as fitz
from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.core.config import get_settings
from app.ml.skill_extractor import extract_skills, spacy_available

DocumentType = Literal["pdf", "docx"]


class ResumeDocumentError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class ExtractedDocument:
    document_type: DocumentType
    text: str
    page_count: int
    contains_images: bool


def detect_document_type(filename: str | None, contents: bytes) -> DocumentType:
    suffix = (filename or "").rsplit(".", maxsplit=1)
    extension = suffix[-1].casefold() if len(suffix) == 2 else ""
    if extension == "pdf":
        if not contents.startswith(b"%PDF-"):
            raise ResumeDocumentError(
                "invalid_pdf", "The uploaded file is not a valid PDF document."
            )
        return "pdf"
    if extension == "docx":
        try:
            with zipfile.ZipFile(BytesIO(contents)) as archive:
                members = archive.infolist()
                uncompressed_total = sum(member.file_size for member in members)
                if (
                    len(members) > 500
                    or uncompressed_total > 50 * 1024 * 1024
                    or any(member.file_size > 20 * 1024 * 1024 for member in members)
                    or "[Content_Types].xml" not in archive.namelist()
                    or "word/document.xml" not in archive.namelist()
                ):
                    raise ResumeDocumentError(
                        "invalid_docx", "The uploaded DOCX document is invalid or too complex."
                    )
        except (zipfile.BadZipFile, OSError):
            raise ResumeDocumentError(
                "invalid_docx", "The uploaded file is not a valid DOCX document."
            ) from None
        return "docx"
    raise ResumeDocumentError(
        "unsupported_type", "Only PDF and DOCX resume files are supported."
    )


def extract_document(contents: bytes, document_type: DocumentType) -> ExtractedDocument:
    if document_type == "pdf":
        return _extract_pdf(contents)
    return _extract_docx(contents)


def _extract_pdf(contents: bytes) -> ExtractedDocument:
    try:
        with fitz.open(stream=contents, filetype="pdf") as document:
            if document.is_encrypted:
                raise ResumeDocumentError(
                    "encrypted_pdf",
                    "Password-protected PDFs are not supported. Upload an unlocked PDF.",
                )
            if document.page_count == 0:
                raise ResumeDocumentError("empty_document", "The PDF has no pages.")
            if document.page_count > get_settings().resume_max_pages:
                raise ResumeDocumentError(
                    "too_many_pages",
                    f"Documents may contain at most {get_settings().resume_max_pages} pages.",
                    status_code=413,
                )
            text_parts = []
            extracted_char_count = 0
            contains_images = False
            for page in document:
                page_text = page.get_text("text")
                extracted_char_count += len(page_text)
                if extracted_char_count > get_settings().resume_max_extracted_chars:
                    raise ResumeDocumentError(
                        "document_text_too_large",
                        "The extracted document text exceeds the processing limit.",
                        status_code=413,
                    )
                text_parts.append(page_text)
                contains_images = contains_images or bool(page.get_images(full=True))
            return ExtractedDocument(
                document_type="pdf",
                text="\n".join(text_parts),
                page_count=document.page_count,
                contains_images=contains_images,
            )
    except ResumeDocumentError:
        raise
    except (fitz.FileDataError, fitz.EmptyFileError, RuntimeError, ValueError):
        raise ResumeDocumentError(
            "corrupted_pdf",
            "The PDF could not be read. Check the file or upload another copy.",
        ) from None


def _extract_docx(contents: bytes) -> ExtractedDocument:
    try:
        document = Document(BytesIO(contents))
    except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError, OSError):
        raise ResumeDocumentError(
            "corrupted_docx",
            "The DOCX document could not be read. Check the file or upload another copy.",
        ) from None

    lines = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                lines.append(" | ".join(cells))
    if sum(map(len, lines)) > get_settings().resume_max_extracted_chars:
        raise ResumeDocumentError(
            "document_text_too_large",
            "The extracted document text exceeds the processing limit.",
            status_code=413,
        )
    return ExtractedDocument(
        document_type="docx",
        text="\n".join(lines),
        page_count=0,
        contains_images=bool(document.inline_shapes),
    )


_SECTION_HEADINGS: dict[str, set[str]] = {
    "skills": {
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "skills and competencies",
        "skills and expertise",
    },
    "education": {"education", "academic background", "academics", "qualifications"},
    "work_experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "career history",
    },
    "projects": {"projects", "selected projects", "personal projects", "project experience"},
    "certifications": {
        "certifications",
        "certificates",
        "licenses and certifications",
        "professional certifications",
        "licenses",
    },
}
_NON_FACT_HEADINGS = {
    "summary",
    "professional summary",
    "profile",
    "objective",
    "career objective",
    "contact",
    "contact information",
    "languages",
    "interests",
    "references",
    "achievements",
    "awards",
}
_HEADING_LOOKUP = {
    re.sub(r"[^a-z ]", "", heading.casefold()).strip(): section
    for section, headings in _SECTION_HEADINGS.items()
    for heading in headings
}
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d().\-\s]{8,}\d)(?!\w)")
_URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s,;]+|(?<![@\w])(?:linkedin\.com/in/|github\.com/)[^\s,;]+",
    re.I,
)


def _heading(line: str) -> str | None:
    normalized = re.sub(r"[^a-z ]", "", line.casefold()).strip()
    return _HEADING_LOOKUP.get(normalized)


def _clean_snippet(text: str) -> str:
    text = _EMAIL_RE.sub("[email redacted]", text)
    text = _PHONE_RE.sub("[phone redacted]", text)
    text = _URL_RE.sub("[link redacted]", text)
    return re.sub(r"\s+", " ", text).strip(" \t|•-")


def extract_resume_facts(text: str, skills: list[str]) -> dict[str, object]:
    sections: dict[str, list[str]] = {
        "skills": [],
        "education": [],
        "work_experience": [],
        "projects": [],
        "certifications": [],
    }
    active_section: str | None = None
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        heading = _heading(cleaned)
        if heading:
            active_section = heading
            continue
        normalized_heading = re.sub(r"[^a-z ]", "", cleaned.casefold()).strip()
        if normalized_heading in _NON_FACT_HEADINGS:
            active_section = None
            continue
        if len(cleaned) < 3 or len(cleaned) > 1000:
            continue
        if active_section and len(sections[active_section]) < 100:
            sections[active_section].append(_clean_snippet(cleaned))

    contacts = {
        "emails": list(dict.fromkeys(_EMAIL_RE.findall(text))),
        "phones": list(dict.fromkeys(match.strip() for match in _PHONE_RE.findall(text))),
        "professional_links": list(dict.fromkeys(_URL_RE.findall(text))),
    }
    evidence: dict[str, list[dict[str, str]]] = {
        section: [
            {"text": value, "source": "resume_text"} for value in values[:100]
        ]
        for section, values in sections.items()
    }
    return {
        "skills": [{"name": skill, "source": "resume_text"} for skill in skills],
        "skill_section_evidence": evidence["skills"],
        "education": evidence["education"],
        "work_experience": evidence["work_experience"],
        "projects": evidence["projects"],
        "certifications": evidence["certifications"],
        "contacts": contacts,
        "has_extractable_text": bool(text.strip()),
    }


def analyze_resume(text: str) -> dict[str, object]:
    skills = extract_skills(text, get_settings().skill_taxonomy_path)
    facts = extract_resume_facts(text, skills)
    if not spacy_available():
        facts["limitations"] = [
            "spaCy is unavailable; skills were matched against the configured taxonomy without NLP segmentation."
        ]
    return facts
