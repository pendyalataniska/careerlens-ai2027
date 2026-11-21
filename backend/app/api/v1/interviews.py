from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.models.candidate import CandidateProfile
from app.models.interview import InterviewSession
from app.models.user import UserRole
from app.schemas.interview import (
    InterviewAnalyticsPublic,
    InterviewAnswerCreate,
    InterviewRolePublic,
    InterviewSessionCreate,
    InterviewSessionList,
    InterviewSessionPublic,
)
from app.services.interview_preparation import (
    InterviewProviderResponseError,
    InterviewProviderUnavailable,
    analytics,
    create_session,
    evaluate_and_save_answer,
    get_owned_session,
    list_roles,
    session_public,
)

router = APIRouter(
    prefix="/interviews",
    tags=["interview preparation"],
    dependencies=[Depends(require_roles(UserRole.CANDIDATE))],
)


@router.get("/roles", response_model=list[InterviewRolePublic])
def get_interview_roles(db: DbSession) -> list[InterviewRolePublic]:
    return [
        InterviewRolePublic(
            id=job.id,
            title=job.title,
            company_name=job.company_name,
            location=job.location,
            required_skills=job.required_skills or [],
        )
        for job in list_roles(db)
    ]


@router.post(
    "/sessions",
    response_model=InterviewSessionPublic,
    status_code=status.HTTP_201_CREATED,
)
def post_interview_session(
    payload: InterviewSessionCreate,
    db: DbSession,
    user: CurrentUser,
) -> InterviewSessionPublic:
    try:
        interview = create_session(
            db,
            user,
            job_id=payload.job_id,
            technical_count=payload.technical_questions,
            hr_count=payload.hr_questions,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InterviewProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InterviewProviderResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return InterviewSessionPublic.model_validate(session_public(interview))


@router.get("/sessions", response_model=InterviewSessionList)
def get_interview_sessions(
    db: DbSession, user: CurrentUser
) -> InterviewSessionList:
    candidate = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")
    sessions = db.scalars(
        select(InterviewSession)
        .options(selectinload(InterviewSession.questions))
        .where(InterviewSession.candidate_id == candidate.id)
        .order_by(InterviewSession.created_at.desc())
    ).all()
    return InterviewSessionList(
        items=[
            InterviewSessionPublic.model_validate(session_public(interview))
            for interview in sessions
        ]
    )


@router.get("/sessions/{session_id}", response_model=InterviewSessionPublic)
def get_interview_session(
    session_id: UUID, db: DbSession, user: CurrentUser
) -> InterviewSessionPublic:
    interview = get_owned_session(db, user, session_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return InterviewSessionPublic.model_validate(session_public(interview))


@router.post(
    "/sessions/{session_id}/questions/{question_id}/answer",
    response_model=InterviewSessionPublic,
)
def submit_answer(
    session_id: UUID,
    question_id: UUID,
    payload: InterviewAnswerCreate,
    db: DbSession,
    user: CurrentUser,
) -> InterviewSessionPublic:
    interview = get_owned_session(db, user, session_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    question = next(
        (item for item in interview.questions if item.id == question_id),
        None,
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Interview question not found.")
    try:
        evaluate_and_save_answer(db, question, interview, payload.answer.strip())
    except InterviewProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InterviewProviderResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    db.refresh(interview)
    return InterviewSessionPublic.model_validate(session_public(interview))


@router.get("/analytics", response_model=InterviewAnalyticsPublic)
def get_interview_analytics(
    db: DbSession, user: CurrentUser
) -> InterviewAnalyticsPublic:
    try:
        return InterviewAnalyticsPublic.model_validate(analytics(db, user))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
