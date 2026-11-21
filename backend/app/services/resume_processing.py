import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.resume import Resume
from app.services.resume_extraction import (
    ResumeDocumentError,
    analyze_resume,
    detect_document_type,
    extract_document,
)
from app.services.resume_storage import PrivateResumeStorage

logger = logging.getLogger(__name__)


def process_resume_record(
    db: Session,
    resume_id: uuid.UUID,
    *,
    settings: Settings,
) -> str:
    resume = db.scalar(select(Resume).where(Resume.id == resume_id))
    if resume is None:
        raise LookupError("Resume record not found.")
    if resume.extraction_status in {"completed", "scanned", "no_text"}:
        return resume.extraction_status

    resume.extraction_status = "processing"
    db.commit()
    try:
        contents = PrivateResumeStorage(settings).read(resume.id, resume.storage_key)
        document_type = detect_document_type(resume.file_name, contents)
        extracted = extract_document(contents, document_type)
        clean_text = extracted.text.strip()
        if clean_text:
            extracted_data = analyze_resume(clean_text)
            status = "completed"
            limitations = [
                "Extracted facts reflect text found in the document and may omit content that could not be recognized."
            ]
            limitations.extend(extracted_data.pop("limitations", []))
            if extracted.contains_images:
                limitations.append("Embedded images are not OCR-processed.")
        else:
            extracted_data = {
                "skills": [],
                "skill_section_evidence": [],
                "education": [],
                "work_experience": [],
                "projects": [],
                "certifications": [],
                "contacts": {
                    "emails": [],
                    "phones": [],
                    "professional_links": [],
                },
                "has_extractable_text": False,
            }
            status = "scanned" if extracted.contains_images else "no_text"
            limitations = [
                "No searchable text was found. OCR is not configured, so no resume facts were extracted."
            ]
        contacts = extracted_data.pop(
            "contacts", {"emails": [], "phones": [], "professional_links": []}
        )
        extracted_data["limitations"] = limitations
        resume.extracted_data = extracted_data
        resume.contact_information_encrypted = PrivateResumeStorage(
            settings
        ).encrypt_metadata(
            resume.id, json.dumps(contacts, ensure_ascii=False).encode("utf-8")
        )
        resume.extraction_status = status
        db.commit()
        return status
    except (ResumeDocumentError, OSError, ValueError):
        db.rollback()
        _mark_failed(db, resume_id)
        logger.warning(
            "Resume background extraction failed",
            extra={"resume_id": str(resume_id)},
            exc_info=True,
        )
        return "failed"
    except Exception:
        db.rollback()
        _mark_failed(db, resume_id)
        logger.exception(
            "Unexpected resume processing failure",
            extra={"resume_id": str(resume_id)},
        )
        raise


def _mark_failed(db: Session, resume_id: uuid.UUID) -> None:
    failed_resume = db.scalar(select(Resume).where(Resume.id == resume_id))
    if failed_resume is None:
        raise LookupError("Resume record not found while recording a failed task.")
    failed_resume.extraction_status = "failed"
    failed_resume.extracted_data = {
        "skills": [],
        "skill_section_evidence": [],
        "education": [],
        "work_experience": [],
        "projects": [],
        "certifications": [],
        "limitations": [
            "The uploaded document could not be processed. Verify the file and upload it again."
        ],
    }
    db.commit()
