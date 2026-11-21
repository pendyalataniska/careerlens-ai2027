from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.job import Job
from app.models.recruiter import RecruiterProfile
from app.models.user import User
from app.schemas.job import JobCreate


def list_jobs(
    db: Session,
    *,
    query: str | None,
    location: str | None,
    employment_type: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Job], int]:
    statement = select(Job).options(joinedload(Job.recruiter))
    filters = [Job.is_active.is_(True)]
    if query:
        search = f"%{query.strip()}%"
        filters.append(or_(Job.title.ilike(search), Job.description.ilike(search)))
    if location:
        filters.append(Job.location.ilike(f"%{location.strip()}%"))
    if employment_type:
        filters.append(Job.employment_type.ilike(employment_type.strip()))
    if filters:
        statement = statement.where(*filters)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    jobs = list(
        db.scalars(
            statement.order_by(Job.created_at.desc()).limit(limit).offset(offset)
        )
    )
    return jobs, total


def get_job(db: Session, job_id: UUID) -> Job | None:
    return db.scalar(
        select(Job)
        .options(joinedload(Job.recruiter))
        .where(Job.id == job_id, Job.is_active.is_(True))
    )


def create_job(db: Session, user: User, request: JobCreate) -> Job:
    recruiter = db.scalar(
        select(RecruiterProfile).where(RecruiterProfile.user_id == user.id)
    )
    if recruiter is None:
        raise RuntimeError("Recruiter profile is missing for recruiter account.")
    job = Job(recruiter=recruiter, **request.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
