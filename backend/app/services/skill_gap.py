import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import PROJECT_ROOT
from app.ml.skill_extractor import extract_skills, load_skill_taxonomy
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.learning_activity import LearningActivity, LearningActivityStatus
from app.models.resume import Resume
from app.models.user import User


@lru_cache(maxsize=1)
def _resource_catalog() -> dict[str, list[dict[str, str]]]:
    path = PROJECT_ROOT / "backend" / "app" / "ml" / "learning_resources.json"
    try:
        catalog: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to load curated learning resources: {path}") from exc
    if not isinstance(catalog, dict):
        raise RuntimeError("Learning resource catalog must be a JSON object.")
    validated: dict[str, list[dict[str, str]]] = {}
    for skill, resources in catalog.items():
        if not isinstance(skill, str) or not isinstance(resources, list):
            raise RuntimeError("Learning resource catalog entries are invalid.")
        validated[skill] = []
        for resource in resources:
            if not isinstance(resource, dict) or not all(
                isinstance(resource.get(field), str) and resource[field]
                for field in ("id", "title", "provider", "url", "description")
            ):
                raise RuntimeError(f"Learning resources for {skill!r} are invalid.")
            validated[skill].append(resource)
    return validated


def _skill_name_map() -> dict[str, str]:
    return {
        alias.casefold(): canonical
        for canonical, aliases in load_skill_taxonomy().items()
        for alias in aliases
    }


def _canonicalize(skills: list[str] | tuple[str, ...]) -> set[str]:
    name_map = _skill_name_map()
    return {
        name_map[skill.casefold()]
        for skill in skills
        if skill.casefold() in name_map
    }


def _candidate_and_resume(db: Session, user: User) -> tuple[CandidateProfile, Resume]:
    candidate = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    if candidate is None:
        raise LookupError("Candidate profile not found.")
    resume = db.scalar(
        select(Resume)
        .where(
            Resume.candidate_id == candidate.id,
            Resume.extraction_status == "completed",
        )
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    if resume is None:
        raise LookupError("No analyzed resume was found for this candidate.")
    return candidate, resume


def analyze_skill_gaps(
    db: Session,
    user: User,
    job_id: UUID,
) -> dict[str, Any]:
    candidate, resume = _candidate_and_resume(db, user)
    job = db.scalar(
        select(Job)
        .options(joinedload(Job.recruiter))
        .where(Job.id == job_id, Job.is_active.is_(True))
    )
    if job is None:
        raise LookupError("Active job not found.")

    extracted = resume.extracted_data
    explicit_skills = _canonicalize(
        [
            item["name"]
            for item in extracted.get("skills", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]
    )
    skill_section_skills = _canonicalize(
        extract_skills(
            "\n".join(
                item["text"]
                for item in extracted.get("skill_section_evidence", [])
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
        )
    )
    experience_skills: set[str] = set()
    for evidence in extracted.get("work_experience", []):
        if isinstance(evidence, dict) and isinstance(evidence.get("text"), str):
            experience_skills.update(extract_skills(evidence["text"]))
    experience_skills = _canonicalize(list(experience_skills)) - explicit_skills

    required: list[str] = []
    aliases = _skill_name_map()
    for skill in job.required_skills or []:
        canonical = aliases.get(skill.casefold())
        if canonical and canonical.casefold() not in {
            entry.casefold() for entry in required
        }:
            required.append(canonical)
        elif not canonical and skill.strip().casefold() not in {
            entry.casefold() for entry in required
        }:
            required.append(skill.strip())

    activities = list(
        db.scalars(
            select(LearningActivity).where(
                LearningActivity.candidate_id == candidate.id
            )
        )
    )
    activity_by_resource = {
        (activity.skill.casefold(), activity.resource_id): activity
        for activity in activities
    }
    catalog = _resource_catalog()
    resource_skill_map = {key.casefold(): key for key in catalog}

    categorized: dict[str, list[dict[str, Any]]] = {
        "strong_matches": [],
        "partial_matches": [],
        "missing_skills": [],
    }
    for skill in required:
        if skill in skill_section_skills:
            category = "strong_match"
            explanation = "This skill was found under a recognized Skills section in the analyzed resume."
            bucket = "strong_matches"
        elif skill in experience_skills:
            category = "partial_match"
            explanation = (
                "This skill appears in extracted work-experience text but was not "
                "found under a recognized Skills section; review the evidence."
            )
            bucket = "partial_matches"
        elif skill in explicit_skills:
            category = "partial_match"
            explanation = (
                "This taxonomy skill was found in resume text outside a recognized "
                "Skills section; review the source context before relying on it."
            )
            bucket = "partial_matches"
        else:
            category = "missing"
            explanation = (
                "No matching skill was found in the analyzed resume's extracted "
                "skills or work-experience evidence."
            )
            bucket = "missing_skills"

        catalog_skill = resource_skill_map.get(skill.casefold())
        resources = catalog.get(catalog_skill, []) if catalog_skill else []
        resource_views = []
        progress_values = []
        for resource in resources:
            activity = activity_by_resource.get((skill.casefold(), resource["id"]))
            resource_views.append(
                {
                    **resource,
                    "status": activity.status if activity else None,
                    "activity_id": activity.id if activity else None,
                }
            )
            progress_values.append(
                100
                if activity and activity.status == LearningActivityStatus.COMPLETED
                else 50
                if activity and activity.status == LearningActivityStatus.IN_PROGRESS
                else 0
            )

        categorized[bucket].append(
            {
                "skill": skill,
                "category": category,
                "explanation": explanation,
                "learning_progress": (
                    round(sum(progress_values) / len(progress_values))
                    if progress_values
                    else 0
                ),
                "resources": resource_views if category != "strong_match" else [],
            }
        )

    for entries in categorized.values():
        entries.sort(key=lambda item: item["skill"].casefold())
    return {
        "job_id": job.id,
        "job_title": job.title,
        "resume_id": resume.id,
        **categorized,
        "evidence_note": (
            "Strong means found under a recognized Skills section. Partial means "
            "found in extracted work-experience evidence or elsewhere in resume "
            "text outside that section. Missing means no taxonomy match was found "
            "in extracted resume text. These labels do not measure "
            "proficiency, verify qualifications, or predict job performance. "
            "Learning progress reflects self-reported resource activity."
        ),
    }


def list_related_jobs(
    db: Session,
    user: User,
    limit: int = 10,
) -> list[dict[str, Any]]:
    _, resume = _candidate_and_resume(db, user)
    explicit_skills = _canonicalize(
        [
            item["name"]
            for item in resume.extracted_data.get("skills", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]
    )
    taxonomy_map = _skill_name_map()
    jobs = list(
        db.scalars(
            select(Job)
            .options(joinedload(Job.recruiter))
            .where(Job.is_active.is_(True))
        )
    )
    results = []
    for job in jobs:
        required = []
        for skill in job.required_skills or []:
            canonical = taxonomy_map.get(skill.casefold(), skill.strip())
            if canonical.casefold() not in {item.casefold() for item in required}:
                required.append(canonical)
        matches = sorted(
            [skill for skill in required if skill in explicit_skills],
            key=str.casefold,
        )
        missing = sorted(
            [skill for skill in required if skill not in explicit_skills],
            key=str.casefold,
        )
        if not matches:
            continue
        results.append(
            {
                "job_id": job.id,
                "title": job.title,
                "company_name": job.company_name,
                "location": job.location,
                "matching_skills": matches,
                "missing_skills": missing,
                "explanation": (
                    f"This active job listing shares {len(matches)} taxonomy skill "
                    "mention(s) found in resume text. Relatedness is based on skill "
                    "overlap only, not a hiring prediction."
                ),
            }
        )
    results.sort(
        key=lambda item: (
            -len(item["matching_skills"]),
            len(item["missing_skills"]),
            item["title"].casefold(),
        )
    )
    return results[:limit]
