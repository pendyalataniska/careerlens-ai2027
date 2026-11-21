import hashlib
import logging
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.core.config import get_settings
from app.models.candidate import CandidateProfile
from app.models.resume import Resume
from app.models.user import UserRole
from app.schemas.resume import ResumeAnalysisPublic, ResumePublic
from app.schemas.resume import ResumeTaskPublic
from app.services.resume_extraction import ResumeDocumentError, detect_document_type
from app.services.resume_processing import process_resume_record
from app.services.resume_storage import PrivateResumeStorage

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/resumes",
    tags=["resumes"],
    dependencies=[Depends(require_roles(UserRole.CANDIDATE))],
)
_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _safe_filename(filename: str | None) -> str:
    name = (filename or "resume").replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:255] or "resume"


def _get_owned_resume(db: DbSession, resume_id: uuid.UUID, user_id: uuid.UUID) -> Resume:
    resume = db.scalar(
        select(Resume)
        .join(CandidateProfile, Resume.candidate_id == CandidateProfile.id)
        .where(Resume.id == resume_id, CandidateProfile.user_id == user_id)
    )
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )
    return resume


@router.post(
    "/upload",
    response_model=ResumePublic,
    status_code=status.HTTP_201_CREATED,
)
def upload_resume(
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
) -> ResumePublic:
    settings = get_settings()
    chunks: list[bytes] = []
    total_bytes = 0
    try:
        while chunk := file.file.read(64 * 1024):
            total_bytes += len(chunk)
            if total_bytes > settings.resume_max_file_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Resume exceeds the {settings.resume_max_file_size_bytes}-byte upload limit.",
                )
            chunks.append(chunk)
    finally:
        file.file.close()
    contents = b"".join(chunks)
    try:
        document_type = detect_document_type(file.filename, contents)
    except ResumeDocumentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.args[0]) from None
    if file.content_type not in (None, "", "application/octet-stream", _CONTENT_TYPES[document_type]):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The declared file type does not match the resume document.",
        )

    candidate = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )
    resume_id = uuid.uuid4()
    storage = PrivateResumeStorage(settings)
    resume = Resume(
        id=resume_id,
        candidate_id=candidate.id,
        file_name=_safe_filename(file.filename),
        storage_key=f"{resume_id.hex}.clrs",
        content_type=_CONTENT_TYPES[document_type],
        file_size_bytes=total_bytes,
        sha256_digest=hashlib.sha256(contents).hexdigest(),
        extraction_status="pending",
    )
    storage_key = ""
    try:
        storage_key = storage.save(resume_id, contents)
        resume.storage_key = storage_key
        db.add(resume)
        db.commit()
        db.refresh(resume)
    except (OSError, SQLAlchemyError):
        db.rollback()
        if storage_key:
            try:
                storage.delete(storage_key)
            except OSError:
                logger.exception(
                    "Encrypted resume cleanup failed after database error",
                    extra={"resume_id": str(resume_id)},
                )
        logger.exception(
            "Resume upload could not be persisted",
            extra={"resume_id": str(resume_id), "user_id": str(user.id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The resume could not be stored. Please try again.",
        ) from None
    if settings.celery_task_always_eager:
        process_resume_record(db, resume.id, settings=settings)
    else:
        try:
            from app.tasks.resume_tasks import process_resume_task

            task = process_resume_task.apply_async(
                args=[str(resume.id), str(storage.root)]
            )
            resume.task_id = task.id
            db.commit()
            db.refresh(resume)
        except Exception as exc:
            db.rollback()
            resume = db.scalar(select(Resume).where(Resume.id == resume_id))
            if resume:
                resume.extraction_status = "failed"
                resume.extracted_data = {
                    "limitations": [
                        "Background resume processing could not be queued. Please retry the upload."
                    ]
                }
                db.commit()
            logger.exception(
                "Resume processing could not be queued",
                extra={"resume_id": str(resume_id), "user_id": str(user.id)},
            )
            raise HTTPException(
                status_code=503,
                detail="Resume processing is temporarily unavailable.",
            ) from exc
    return ResumePublic.model_validate(resume)


@router.get("", response_model=list[ResumePublic])
def list_resumes(db: DbSession, user: CurrentUser) -> list[ResumePublic]:
    candidate = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")
    resumes = db.scalars(
        select(Resume)
        .where(Resume.candidate_id == candidate.id)
        .order_by(Resume.created_at.desc())
    ).all()
    return [ResumePublic.model_validate(resume) for resume in resumes]


@router.get("/{resume_id}", response_model=ResumePublic)
def get_resume(
    resume_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> ResumePublic:
    resume = _get_owned_resume(db, resume_id, user.id)
    return ResumePublic.model_validate(resume)


@router.get("/{resume_id}/task", response_model=ResumeTaskPublic)
def get_resume_task_status(
    resume_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> ResumeTaskPublic:
    resume = _get_owned_resume(db, resume_id, user.id)
    data = resume.extracted_data
    return ResumeTaskPublic(
        resume_id=resume.id,
        status=resume.extraction_status,
        task_id=resume.task_id,
        limitations=data.get("limitations", []),
    )


@router.get("/{resume_id}/analysis", response_model=ResumeAnalysisPublic)
def get_resume_analysis(
    resume_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> ResumeAnalysisPublic:
    resume = _get_owned_resume(db, resume_id, user.id)
    data = resume.extracted_data
    return ResumeAnalysisPublic(
        resume_id=resume.id,
        extraction_status=resume.extraction_status,
        skills=data.get("skills", []),
        skill_section_evidence=data.get("skill_section_evidence", []),
        education=data.get("education", []),
        work_experience=data.get("work_experience", []),
        projects=data.get("projects", []),
        certifications=data.get("certifications", []),
        limitations=data.get("limitations", []),
    )
