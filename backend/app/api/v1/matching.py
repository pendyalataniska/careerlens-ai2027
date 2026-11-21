import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.core.config import Settings, get_settings
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.matching import MatchingResult
from app.models.resume import Resume
from app.models.user import UserRole
from app.schemas.matching import (
    MatchingAnalyzeRequest,
    MatchingRecommendations,
    MatchingResultPublic,
)
from app.services.matching import (
    SCORING_MODEL_VERSION,
    CandidateProfileData,
    JobProfileData,
    MatchingModelUnavailable,
    calculate_match,
    candidate_profile_from_resume,
    create_matching_result,
    job_profile_from_job,
    persist_profile_embeddings,
    profile_embedding_texts,
    vector_ranked_job_ids,
    vectors_for_pair,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/matching",
    tags=["matching"],
    dependencies=[Depends(require_roles(UserRole.CANDIDATE))],
)


def _candidate_profile(db: DbSession, user_id: uuid.UUID) -> CandidateProfile:
    profile = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )
    return profile


def _candidate_resume(
    db: DbSession, candidate_id: uuid.UUID, resume_id: uuid.UUID | None
) -> Resume:
    statement = select(Resume).where(
        Resume.candidate_id == candidate_id,
        Resume.extraction_status == "completed",
    )
    if resume_id:
        statement = statement.where(Resume.id == resume_id)
    else:
        statement = statement.order_by(Resume.created_at.desc())
    resume = db.scalar(statement.limit(1))
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analyzed resume was found for this candidate.",
        )
    return resume


def _active_job(db: DbSession, job_id: uuid.UUID) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.is_active.is_(True)))
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active job not found.",
        )
    return job


def _match_profiles(
    db: DbSession,
    candidate: CandidateProfileData,
    candidate_id: uuid.UUID,
    job: Job,
    settings: Settings,
):
    job_profile = job_profile_from_job(job)
    texts = {
        (owner_type, candidate_id if owner_type == "candidate" else job.id, kind): text
        for (owner_type, kind), text in profile_embedding_texts(candidate, job_profile).items()
    }
    vectors = persist_profile_embeddings(db, texts, settings=settings)
    score = calculate_match(
        candidate,
        job_profile,
        vectors_for_pair(candidate_id, job.id, vectors),
        settings,
    )
    return score


@router.post(
    "/analyze",
    response_model=MatchingResultPublic,
    status_code=status.HTTP_201_CREATED,
)
def analyze_match(
    payload: MatchingAnalyzeRequest,
    db: DbSession,
    user: CurrentUser,
) -> MatchingResultPublic:
    settings = get_settings()
    candidate_profile = _candidate_profile(db, user.id)
    resume = _candidate_resume(db, candidate_profile.id, payload.resume_id)
    job = _active_job(db, payload.job_id)
    candidate = candidate_profile_from_resume(resume)
    try:
        computation = _match_profiles(
            db, candidate, candidate_profile.id, job, settings
        )
    except MatchingModelUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    result = create_matching_result(
        db, candidate_profile.id, resume.id, job.id, computation
    )
    db.commit()
    db.refresh(result)
    return MatchingResultPublic.model_validate(result)


@router.get(
    "/recommendations",
    response_model=MatchingRecommendations,
)
def get_recommendations(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=50),
    resume_id: uuid.UUID | None = None,
) -> MatchingRecommendations:
    settings = get_settings()
    candidate_profile = _candidate_profile(db, user.id)
    resume = _candidate_resume(db, candidate_profile.id, resume_id)
    candidate = candidate_profile_from_resume(resume)
    jobs = list(
        db.scalars(
            select(Job)
            .options(joinedload(Job.recruiter))
            .where(Job.is_active.is_(True))
            .order_by(Job.created_at.desc())
            .limit(settings.matching_max_search_candidates)
        )
    )
    if not jobs:
        return MatchingRecommendations(
            items=[],
            limit=limit,
            scoring_policy=_scoring_policy(settings),
            scoring_model_version=SCORING_MODEL_VERSION,
        )

    texts: dict[tuple[str, uuid.UUID, str], str] = {}
    for (owner_type, kind), text in profile_embedding_texts(
        candidate, job_profile_from_job(jobs[0])
    ).items():
        texts[(owner_type, candidate_profile.id if owner_type == "candidate" else jobs[0].id, kind)] = text
    for job in jobs[1:]:
        for (owner_type, kind), text in profile_embedding_texts(
            CandidateProfileData((), (), None, 0, ()), job_profile_from_job(job)
        ).items():
            texts[(owner_type, job.id, kind)] = text

    try:
        vectors = persist_profile_embeddings(db, texts, settings=settings)
        ranked_ids = vector_ranked_job_ids(
            db,
            jobs,
            candidate_profile.id,
            vectors,
            limit,
            settings,
        )
        job_by_id = {job.id: job for job in jobs}
        ranked_jobs = [job_by_id[job_id] for job_id in ranked_ids]
        ranked_results: list[tuple[float, Job, dict]] = []
        for job in ranked_jobs:
            profile = job_profile_from_job(job)
            score = calculate_match(
                candidate,
                profile,
                vectors_for_pair(candidate_profile.id, job.id, vectors),
                settings,
            )
            ranked_results.append((score["total_score"], job, score))
    except MatchingModelUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    ranked_results.sort(key=lambda item: (-item[0], item[1].created_at, str(item[1].id)))
    output: list[MatchingResultPublic] = []
    for _, job, computation in ranked_results[:limit]:
        result = create_matching_result(
            db, candidate_profile.id, resume.id, job.id, computation
        )
        output.append(MatchingResultPublic.model_validate(result))
    db.commit()
    return MatchingRecommendations(
        items=output,
        limit=limit,
        scoring_policy=_scoring_policy(settings),
        scoring_model_version=SCORING_MODEL_VERSION,
    )


@router.get("/{match_id}", response_model=MatchingResultPublic)
def get_matching_result(
    match_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> MatchingResultPublic:
    result = db.scalar(
        select(MatchingResult)
        .join(CandidateProfile, CandidateProfile.id == MatchingResult.candidate_id)
        .where(MatchingResult.id == match_id, CandidateProfile.user_id == user.id)
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matching result not found.",
        )
    return MatchingResultPublic.model_validate(result)


def _scoring_policy(settings: Settings) -> dict[str, float]:
    return {
        "skill_compatibility": settings.matching_skill_weight,
        "relevant_experience": settings.matching_experience_weight,
        "description_semantic_similarity": settings.matching_semantic_weight,
        "education_relevance": settings.matching_education_weight,
    }
