from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.ml.skill_extractor import extract_skills, load_skill_taxonomy
from app.models.job import Job
from app.models.matching import MatchingEmbedding, MatchingResult
from app.models.resume import Resume
from app.services.resume_extraction import ResumeDocumentError

logger = logging.getLogger(__name__)
SCORING_MODEL_VERSION = "careerlens-weighted-evidence-v1"
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current)\b", re.I)
_DEGREE_TERMS = (
    "doctorate",
    "phd",
    "ph.d",
    "master",
    "bachelor",
    "associate",
    "high school",
)


class MatchingModelUnavailable(RuntimeError):
    """Raised when the configured embedding model cannot be loaded."""


@dataclass(frozen=True)
class CandidateProfileData:
    skills: tuple[str, ...]
    experience_skills: tuple[str, ...]
    experience_years: float | None
    work_evidence_count: int
    education: tuple[str, ...]


@dataclass(frozen=True)
class JobProfileData:
    title: str
    required_skills: tuple[str, ...]
    description_skills: tuple[str, ...]
    minimum_experience_years: int | None
    required_education: str | None


class SentenceTransformerEncoder:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            encoded = _load_sentence_transformer(
                self.settings.matching_embedding_model
            ).encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            logger.exception(
                "Sentence Transformer encoding failed",
                extra={"model_name": self.settings.matching_embedding_model},
            )
            raise MatchingModelUnavailable(
                "The configured semantic embedding model could not encode the profiles."
            ) from exc
        vectors = np.asarray(encoded, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.shape[1] != self.settings.matching_embedding_dimensions:
            raise MatchingModelUnavailable(
                "The embedding model output dimensions do not match "
                "MATCHING_EMBEDDING_DIMENSIONS."
            )
        return vectors.tolist()


@lru_cache(maxsize=2)
def _load_sentence_transformer(model_name: str) -> Any:
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)
    except Exception as exc:
        logger.exception(
            "Sentence Transformer model could not be loaded",
            extra={"model_name": model_name},
        )
        raise MatchingModelUnavailable(
            "The semantic matching model is unavailable. Install sentence-transformers "
            "and make the configured model available locally or through the model registry."
        ) from exc


def _strings(items: object, key: str | None = None) -> list[str]:
    if not isinstance(items, list):
        return []
    values: list[str] = []
    for item in items:
        if isinstance(item, str):
            candidate = item
        elif isinstance(item, dict) and key and isinstance(item.get(key), str):
            candidate = item[key]
        else:
            continue
        cleaned = candidate.strip()
        if cleaned:
            values.append(cleaned)
    return values


def candidate_profile_from_resume(resume: Resume) -> CandidateProfileData:
    data = resume.extracted_data
    skills = tuple(dict.fromkeys(_strings(data.get("skills"), "name")))
    work = _strings(data.get("work_experience"), "text")
    experience_skills = tuple(
        dict.fromkeys(skill for evidence in work for skill in extract_skills(evidence))
    )
    education = tuple(dict.fromkeys(_strings(data.get("education"), "text")))
    years = _experience_years(work)
    return CandidateProfileData(
        skills=skills,
        experience_skills=experience_skills,
        experience_years=years,
        work_evidence_count=len(work),
        education=education,
    )


def job_profile_from_job(job: Job) -> JobProfileData:
    explicit = _strings(job.required_skills)
    canonical = _canonicalize_skills(explicit)
    description_skills = tuple(
        dict.fromkeys(extract_skills(f"{job.title}\n{job.description}"))
    )
    return JobProfileData(
        title=job.title.strip(),
        required_skills=canonical,
        description_skills=description_skills,
        minimum_experience_years=job.minimum_experience_years,
        required_education=job.required_education.strip()
        if job.required_education and job.required_education.strip()
        else None,
    )


def _canonicalize_skills(skills: list[str]) -> tuple[str, ...]:
    taxonomy = load_skill_taxonomy()
    aliases = {
        alias.casefold(): canonical
        for canonical, names in taxonomy.items()
        for alias in names
    }
    return tuple(
        dict.fromkeys(
            aliases.get(skill.casefold(), skill)
            for skill in (value.strip() for value in skills)
            if skill
        )
    )


def _experience_years(work_evidence: list[str]) -> float | None:
    current_year = datetime.now(timezone.utc).year
    periods: list[tuple[int, int]] = []
    for line in work_evidence:
        for start_text, end_text in _YEAR_RE.findall(line):
            start = int(start_text)
            end = current_year if end_text.casefold() in {"present", "current"} else int(end_text)
            if start <= end <= current_year + 1 and end - start <= 60:
                periods.append((start, end))
    if not periods:
        return None
    periods.sort()
    merged: list[list[int]] = []
    for start, end in periods:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return round(sum(end - start for start, end in merged), 1)


def profile_embedding_texts(
    candidate: CandidateProfileData, job: JobProfileData
) -> dict[tuple[str, str], str]:
    texts: dict[tuple[str, str], str] = {}
    if candidate.skills:
        texts[("candidate", "skills")] = "Candidate skills: " + ", ".join(candidate.skills)
    if candidate.experience_skills:
        texts[("candidate", "experience")] = (
            "Skills used in work experience: " + ", ".join(candidate.experience_skills)
        )
    if job.title:
        texts[("job", "description")] = (
            f"Role: {job.title}. Job-related skills mentioned: "
            + (", ".join(job.description_skills) if job.description_skills else "none")
        )
    if job.required_skills:
        texts[("job", "requirements")] = (
            "Explicitly required skills: " + ", ".join(job.required_skills)
        )
    return texts


def cosine_score(left: list[float], right: list[float]) -> float:
    similarity = _cosine_similarity(left, right)
    return min(1.0, max(0.0, similarity))


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    try:
        from sklearn.metrics.pairwise import cosine_similarity

        return float(cosine_similarity([left], [right])[0][0])
    except (ImportError, OSError):
        logger.warning(
            "Scikit-learn native dependencies are unavailable; using NumPy cosine similarity"
        )
    left_vector = np.asarray(left, dtype=np.float64)
    right_vector = np.asarray(right, dtype=np.float64)
    if left_vector.shape != right_vector.shape:
        raise ValueError("Embedding vectors have incompatible dimensions.")
    denominator = float(np.linalg.norm(left_vector) * np.linalg.norm(right_vector))
    if denominator == 0:
        return 0.0
    return float(np.dot(left_vector, right_vector) / denominator)


def _education_match(candidate: CandidateProfileData, requirement: str) -> bool:
    normalized_requirement = " ".join(requirement.casefold().split())
    return any(
        normalized_requirement in " ".join(item.casefold().split())
        for item in candidate.education
    )


def calculate_match(
    candidate: CandidateProfileData,
    job: JobProfileData,
    embeddings: dict[str, list[float]],
    settings: Settings | None = None,
) -> dict[str, Any]:
    config = settings or get_settings()
    required = {skill.casefold(): skill for skill in job.required_skills}
    available = {skill.casefold(): skill for skill in candidate.skills}
    matching_skills = [
        required[key] for key in required.keys() & available.keys()
    ]
    missing_skills = [
        required[key] for key in required.keys() - available.keys()
    ]

    weighted_components: dict[str, tuple[float, float, str]] = {}
    if job.required_skills:
        skill_score = len(matching_skills) / len(job.required_skills)
        weighted_components["skill_compatibility"] = (
            skill_score,
            config.matching_skill_weight,
            f"{len(matching_skills)} of {len(job.required_skills)} explicitly required skills are present.",
        )

    experience_criteria: list[float] = []
    experience_explanations: list[str] = []
    comparison_skills = job.required_skills or job.description_skills
    if comparison_skills:
        work_skills = {skill.casefold() for skill in candidate.experience_skills}
        matched_experience_skills = sum(
            skill.casefold() in work_skills for skill in comparison_skills
        )
        experience_criteria.append(matched_experience_skills / len(comparison_skills))
        experience_explanations.append(
            f"{matched_experience_skills} of {len(comparison_skills)} job-related skills "
            "were found in extracted work-experience evidence."
        )
    if job.minimum_experience_years is not None:
        years_score = (
            min(candidate.experience_years / job.minimum_experience_years, 1.0)
            if candidate.experience_years is not None and job.minimum_experience_years > 0
            else 1.0
            if job.minimum_experience_years == 0
            else 0.0
        )
        experience_criteria.append(years_score)
        evidence = (
            f"{candidate.experience_years:g} dated years found against "
            f"{job.minimum_experience_years} requested."
            if candidate.experience_years is not None
            else "No date ranges were found in extracted experience evidence."
        )
        experience_explanations.append(evidence)
    if experience_criteria:
        weighted_components["relevant_experience"] = (
            min(experience_criteria),
            config.matching_experience_weight,
            " ".join(experience_explanations),
        )

    semantic_pairs: list[tuple[float, str]] = []
    if "candidate_skills" in embeddings and "job_description" in embeddings:
        semantic_pairs.append(
            (
                cosine_score(
                    embeddings["candidate_skills"], embeddings["job_description"]
                ),
                "candidate skills vs. taxonomy skills mentioned in the job description",
            )
        )
    if "candidate_experience" in embeddings and "job_requirements" in embeddings:
        semantic_pairs.append(
            (
                cosine_score(
                    embeddings["candidate_experience"], embeddings["job_requirements"]
                ),
                "skills found in work evidence vs. explicit job requirements",
            )
        )
    if semantic_pairs:
        semantic_score = sum(score for score, _ in semantic_pairs) / len(semantic_pairs)
        pair_explanations = "; ".join(description for _, description in semantic_pairs)
        weighted_components["description_semantic_similarity"] = (
            semantic_score,
            config.matching_semantic_weight,
            f"Cosine similarity over {pair_explanations}. The embedding inputs contain "
            "taxonomy skill names and role title only, not free-form personal details.",
        )

    if job.required_education:
        education_score = float(_education_match(candidate, job.required_education))
        weighted_components["education_relevance"] = (
            education_score,
            config.matching_education_weight,
            (
                f"Explicit education requirement {job.required_education!r} "
                + ("was" if education_score else "was not")
                + " found in extracted education evidence."
            ),
        )

    weight_total = sum(weight for _, weight, _ in weighted_components.values())
    if weight_total <= 0:
        raise ValueError("No matching score components are configured for this job.")
    total_score = sum(
        score * weight for score, weight, _ in weighted_components.values()
    ) / weight_total
    components = {
        name: {
            "score": round(score, 6),
            "configured_weight": weight,
            "effective_weight": round(weight / weight_total, 6),
            "explanation": explanation,
        }
        for name, (score, weight, explanation) in weighted_components.items()
    }
    configured_components = {
        "skill_compatibility": config.matching_skill_weight,
        "relevant_experience": config.matching_experience_weight,
        "description_semantic_similarity": config.matching_semantic_weight,
        "education_relevance": config.matching_education_weight,
    }
    skipped = [
        name
        for name, weight in configured_components.items()
        if weight > 0 and name not in components
    ]
    explanations = [
        f"{name.replace('_', ' ').capitalize()}: {details['explanation']}"
        for name, details in components.items()
    ]
    if skipped:
        explanations.append(
            "Not included because evidence was unavailable or the job did not state "
            "the criterion: " + ", ".join(skipped) + "."
        )
    if missing_skills:
        explanations.append(
            "Missing explicitly required skills: " + ", ".join(missing_skills) + "."
        )
    elif job.required_skills:
        explanations.append("All explicitly required skills were found in the resume.")
    explanations.append(
        "Protected traits (including age, gender, religion, caste, and photographs) "
        "are not used as ranking features."
    )
    return {
        "total_score": round(total_score * 100, 4),
        "score_details": {
            "matching_skills": sorted(matching_skills, key=str.casefold),
            "missing_required_skills": sorted(missing_skills, key=str.casefold),
            "components": components,
            "explanations": explanations,
            "scoring_model_version": SCORING_MODEL_VERSION,
            "score_completeness": "partial" if skipped else "complete",
        },
        "scoring_model_version": SCORING_MODEL_VERSION,
    }


def persist_profile_embeddings(
    db: Session,
    texts: dict[tuple[str, uuid.UUID, str], str],
    settings: Settings | None = None,
    encoder: SentenceTransformerEncoder | None = None,
) -> dict[tuple[str, uuid.UUID, str], list[float]]:
    config = settings or get_settings()
    encoder = encoder or SentenceTransformerEncoder(config)
    candidate_ids = {
        owner_id for (owner_type, owner_id, _), _ in texts.items() if owner_type == "candidate"
    }
    job_ids = {
        owner_id for (owner_type, owner_id, _), _ in texts.items() if owner_type == "job"
    }
    owner_filters = []
    if candidate_ids:
        owner_filters.append(MatchingEmbedding.candidate_id.in_(candidate_ids))
    if job_ids:
        owner_filters.append(MatchingEmbedding.job_id.in_(job_ids))
    existing_rows = list(
        db.scalars(
            select(MatchingEmbedding).where(
                MatchingEmbedding.model_name == config.matching_embedding_model,
                or_(*owner_filters) if owner_filters else False,
            )
        )
    )
    existing = {
        (
            "candidate" if row.candidate_id else "job",
            row.candidate_id or row.job_id,
            row.embedding_kind,
        ): row
        for row in existing_rows
    }
    changed: list[tuple[str, uuid.UUID, str, str, str]] = []
    vectors: dict[tuple[str, uuid.UUID, str], list[float]] = {}
    for (owner_type, owner_id, kind), content in texts.items():
        key = (owner_type, owner_id, kind)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        row = existing.get(key)
        if row is not None and row.content_hash == content_hash:
            vectors[key] = list(row.embedding)
        else:
            changed.append((owner_type, owner_id, kind, content, content_hash))

    new_vectors = encoder.encode([content for _, _, _, content, _ in changed])
    if len(new_vectors) != len(changed):
        raise MatchingModelUnavailable(
            "The embedding model returned a different number of vectors than requested."
        )
    for (owner_type, owner_id, kind, _, content_hash), vector in zip(changed, new_vectors):
        key = (owner_type, owner_id, kind)
        row = existing.get(key)
        if row is None:
            row = MatchingEmbedding(
                candidate_id=owner_id if owner_type == "candidate" else None,
                job_id=owner_id if owner_type == "job" else None,
                embedding_kind=kind,
                model_name=config.matching_embedding_model,
                content_hash=content_hash,
                embedding=vector,
            )
            db.add(row)
        else:
            row.content_hash = content_hash
            row.embedding = vector
        vectors[key] = vector
    db.flush()
    return vectors


def vector_ranked_job_ids(
    db: Session,
    jobs: list[Job],
    candidate_id: uuid.UUID,
    vectors: dict[tuple[str, uuid.UUID, str], list[float]],
    limit: int,
    settings: Settings | None = None,
) -> list[uuid.UUID]:
    config = settings or get_settings()
    candidate_vector = vectors.get(("candidate", candidate_id, "skills"))
    if candidate_vector is None:
        return [job.id for job in jobs]

    job_ids = [job.id for job in jobs]
    search_limit = min(config.matching_max_search_candidates, len(job_ids))
    if db.get_bind().dialect.name == "postgresql":
        statement = (
            select(MatchingEmbedding.job_id)
            .join(Job, Job.id == MatchingEmbedding.job_id)
            .where(
                MatchingEmbedding.job_id.in_(job_ids),
                MatchingEmbedding.embedding_kind == "description",
                MatchingEmbedding.model_name == config.matching_embedding_model,
                Job.is_active.is_(True),
            )
            .order_by(MatchingEmbedding.embedding.cosine_distance(candidate_vector))
            .limit(search_limit)
        )
        ordered_ids = list(db.scalars(statement))
    else:
        job_vectors = [
            vectors.get(("job", job.id, "description")) for job in jobs
        ]
        comparable = [
            (job.id, vector)
            for job, vector in zip(jobs, job_vectors)
            if vector is not None
        ]
        if comparable:
            similarities = [
                _cosine_similarity(candidate_vector, vector)
                for _, vector in comparable
            ]
            ordered_ids = [
                job_id
                for (job_id, _), _score in sorted(
                    zip(comparable, similarities),
                    key=lambda item: float(item[1]),
                    reverse=True,
                )[:search_limit]
            ]
        else:
            ordered_ids = []
    seen = set(ordered_ids)
    ordered_ids.extend(job_id for job_id in job_ids if job_id not in seen)
    return ordered_ids


def vectors_for_pair(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    vectors: dict[tuple[str, uuid.UUID, str], list[float]],
) -> dict[str, list[float]]:
    aliases = {
        "candidate_skills": ("candidate", candidate_id, "skills"),
        "candidate_experience": ("candidate", candidate_id, "experience"),
        "job_description": ("job", job_id, "description"),
        "job_requirements": ("job", job_id, "requirements"),
    }
    return {
        output_key: vectors[source_key]
        for output_key, source_key in aliases.items()
        if source_key in vectors
    }


def create_matching_result(
    db: Session,
    candidate_id: uuid.UUID,
    resume_id: uuid.UUID,
    job_id: uuid.UUID,
    computation: dict[str, Any],
) -> MatchingResult:
    result = MatchingResult(
        candidate_id=candidate_id,
        resume_id=resume_id,
        job_id=job_id,
        total_score=computation["total_score"],
        score_details=computation["score_details"],
        scoring_model_version=computation["scoring_model_version"],
    )
    db.add(result)
    db.flush()
    return result
