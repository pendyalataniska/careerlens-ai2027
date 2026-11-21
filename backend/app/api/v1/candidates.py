from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.models.user import UserRole
from app.models.interview import InterviewSession
from app.models.job import Job
from app.models.matching import MatchingResult
from app.models.resume import Resume
from app.schemas.candidate import (
    CandidateDashboardJob,
    CandidateDashboardPublic,
    CandidateProfilePublic,
    CandidateProfileUpdate,
)
from app.services.candidates import get_candidate_profile, update_candidate_profile

router = APIRouter(
    prefix="/candidates",
    tags=["candidates"],
    dependencies=[Depends(require_roles(UserRole.CANDIDATE))],
)


@router.get("/profile", response_model=CandidateProfilePublic)
def get_profile(db: DbSession, user: CurrentUser) -> CandidateProfilePublic:
    profile = get_candidate_profile(db, user)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )
    return CandidateProfilePublic.model_validate(profile)


@router.put("/profile", response_model=CandidateProfilePublic)
def put_profile(
    payload: CandidateProfileUpdate, db: DbSession, user: CurrentUser
) -> CandidateProfilePublic:
    profile = update_candidate_profile(db, user, payload)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )
    return CandidateProfilePublic.model_validate(profile)


@router.get("/dashboard", response_model=CandidateDashboardPublic)
def get_dashboard(db: DbSession, user: CurrentUser) -> CandidateDashboardPublic:
    profile = get_candidate_profile(db, user)
    if profile is None:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")
    latest_resume = db.scalar(
        select(Resume)
        .where(Resume.candidate_id == profile.id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    match_rows = db.execute(
        select(MatchingResult, Job)
        .join(Job, Job.id == MatchingResult.job_id)
        .options(joinedload(Job.recruiter))
        .where(MatchingResult.candidate_id == profile.id)
        .order_by(MatchingResult.created_at.desc())
        .limit(5)
    ).all()
    session_counts = db.execute(
        select(
            func.count(InterviewSession.id),
            func.count(InterviewSession.id).filter(
                InterviewSession.status == "COMPLETED"
            ),
        ).where(InterviewSession.candidate_id == profile.id)
    ).one()
    disclaimer = (
        "Compatibility scores are transparent policy outputs, not hiring "
        "probabilities or predictions. No score is shown until an actual "
        "matching analysis has been run."
    )
    skills = []
    if latest_resume:
        skills = [
            item["name"]
            for item in latest_resume.extracted_data.get("skills", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]
    return CandidateDashboardPublic(
        profile=CandidateProfilePublic.model_validate(profile),
        latest_resume_id=latest_resume.id if latest_resume else None,
        resume_status=latest_resume.extraction_status if latest_resume else None,
        skills=skills,
        matches=[
            CandidateDashboardJob(
                id=job.id,
                title=job.title,
                company_name=job.company_name,
                location=job.location,
                total_score=matching.total_score,
                created_at=matching.created_at,
            )
            for matching, job in match_rows
        ],
        interview_sessions=session_counts[0],
        completed_interviews=session_counts[1],
        disclaimer=disclaimer,
    )
