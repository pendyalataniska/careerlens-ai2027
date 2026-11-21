from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.models.recruiter import RecruiterProfile
from app.models.job import Job
from app.models.user import UserRole
from app.schemas.job import JobCreate, JobList, JobPublic
from app.services.jobs import create_job, get_job, list_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobList)
def get_jobs(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    location: Annotated[str | None, Query(max_length=180)] = None,
    employment_type: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobList:
    jobs, total = list_jobs(
        db,
        query=q,
        location=location,
        employment_type=employment_type,
        limit=limit,
        offset=offset,
    )
    return JobList(
        items=[JobPublic.model_validate(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=JobPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.RECRUITER))],
)
def post_job(payload: JobCreate, db: DbSession, user: CurrentUser) -> JobPublic:
    job = create_job(db, user, payload)
    return JobPublic.model_validate(job)


@router.get(
    "/mine",
    response_model=JobList,
    dependencies=[Depends(require_roles(UserRole.RECRUITER))],
)
def get_my_jobs(
    db: DbSession,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobList:
    recruiter = db.scalar(
        select(RecruiterProfile).where(RecruiterProfile.user_id == user.id)
    )
    if recruiter is None:
        raise HTTPException(status_code=404, detail="Recruiter profile not found.")
    query = (
        select(Job)
        .options(joinedload(Job.recruiter))
        .where(Job.recruiter_id == recruiter.id)
        .order_by(Job.created_at.desc())
    )
    total = db.scalar(
        select(func.count()).select_from(Job).where(Job.recruiter_id == recruiter.id)
    ) or 0
    jobs = db.scalars(query.offset(offset).limit(limit)).all()
    return JobList(
        items=[JobPublic.model_validate(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=JobPublic)
def get_job_by_id(job_id: UUID, db: DbSession) -> JobPublic:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return JobPublic.model_validate(job)
