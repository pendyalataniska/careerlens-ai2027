from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.models.learning_activity import LearningActivity, LearningActivityStatus
from app.models.user import UserRole
from app.schemas.skill_gap import (
    LearningActivityCreate,
    LearningActivityPublic,
    LearningActivityUpdate,
    RelatedJobsPublic,
    SkillGapAnalysisPublic,
)
from app.services.skill_gap import (
    _candidate_and_resume,
    _resource_catalog,
    analyze_skill_gaps,
    list_related_jobs,
)

router = APIRouter(
    prefix="/skill-gaps",
    tags=["skill gaps"],
    dependencies=[Depends(require_roles(UserRole.CANDIDATE))],
)


def _candidate_id(db: DbSession, user: CurrentUser) -> UUID:
    try:
        candidate, _ = _candidate_and_resume(db, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return candidate.id


@router.get("/analysis", response_model=SkillGapAnalysisPublic)
def get_skill_gap_analysis(
    job_id: UUID, db: DbSession, user: CurrentUser
) -> SkillGapAnalysisPublic:
    try:
        return SkillGapAnalysisPublic.model_validate(
            analyze_skill_gaps(db, user, job_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/related-jobs", response_model=RelatedJobsPublic)
def get_related_jobs(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50),
) -> RelatedJobsPublic:
    try:
        items = list_related_jobs(db, user, limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RelatedJobsPublic(items=items)


@router.get("/activities", response_model=list[LearningActivityPublic])
def get_learning_activities(
    db: DbSession, user: CurrentUser
) -> list[LearningActivityPublic]:
    candidate_id = _candidate_id(db, user)
    activities = db.scalars(
        select(LearningActivity)
        .where(LearningActivity.candidate_id == candidate_id)
        .order_by(LearningActivity.updated_at.desc())
    )
    return [LearningActivityPublic.model_validate(item) for item in activities]


@router.post(
    "/activities",
    response_model=LearningActivityPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_learning_activity(
    payload: LearningActivityCreate,
    db: DbSession,
    user: CurrentUser,
) -> LearningActivityPublic:
    candidate_id = _candidate_id(db, user)
    catalog = _resource_catalog()
    skill_resources = catalog.get(payload.skill, [])
    resource = next(
        (item for item in skill_resources if item["id"] == payload.resource_id),
        None,
    )
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The resource is not curated for this skill.",
        )

    activity = db.scalar(
        select(LearningActivity).where(
            LearningActivity.candidate_id == candidate_id,
            LearningActivity.skill == payload.skill,
            LearningActivity.resource_id == payload.resource_id,
        )
    )
    if activity is None:
        activity = LearningActivity(
            candidate_id=candidate_id,
            skill=payload.skill,
            resource_id=payload.resource_id,
            status=payload.status,
        )
        db.add(activity)
    else:
        activity.status = payload.status
    activity.completed_at = (
        datetime.now(timezone.utc)
        if activity.status == LearningActivityStatus.COMPLETED
        else None
    )
    db.commit()
    db.refresh(activity)
    return LearningActivityPublic.model_validate(activity)


@router.patch(
    "/activities/{activity_id}",
    response_model=LearningActivityPublic,
)
def update_learning_activity(
    activity_id: UUID,
    payload: LearningActivityUpdate,
    db: DbSession,
    user: CurrentUser,
) -> LearningActivityPublic:
    candidate_id = _candidate_id(db, user)
    activity = db.scalar(
        select(LearningActivity).where(
            LearningActivity.id == activity_id,
            LearningActivity.candidate_id == candidate_id,
        )
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="Learning activity not found.")
    activity.status = payload.status
    activity.completed_at = (
        datetime.now(timezone.utc)
        if payload.status == LearningActivityStatus.COMPLETED
        else None
    )
    db.commit()
    db.refresh(activity)
    return LearningActivityPublic.model_validate(activity)
