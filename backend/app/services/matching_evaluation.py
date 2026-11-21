from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import Settings, get_settings
from app.services.matching import (
    CandidateProfileData,
    JobProfileData,
    SentenceTransformerEncoder,
    calculate_match,
    _cosine_similarity,
    profile_embedding_texts,
)

DEFAULT_DATASET = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "data"
    / "labeled_matching_examples.json"
)


def ranking_metrics(
    labels_by_query: dict[str, list[int]],
    scores_by_query: dict[str, list[float]],
    k_values: tuple[int, ...] = (1, 3),
) -> dict[str, float]:
    if set(labels_by_query) != set(scores_by_query):
        raise ValueError("Every query must have matching labels and scores.")
    if not labels_by_query:
        raise ValueError("At least one labeled query is required.")

    metrics: dict[str, float] = {}
    for k in k_values:
        if k < 1:
            raise ValueError("k must be a positive integer.")
        precision_values: list[float] = []
        recall_values: list[float] = []
        ndcg_values: list[float] = []
        for query_id, labels in labels_by_query.items():
            scores = scores_by_query[query_id]
            if len(labels) != len(scores) or not labels:
                raise ValueError(
                    f"Query {query_id!r} must have equally sized, non-empty labels and scores."
                )
            if any(label < 0 for label in labels):
                raise ValueError("Relevance labels must be non-negative.")
            if not all(float(label).is_integer() for label in labels):
                raise ValueError("Relevance labels must be integer grades.")
            if not all(math.isfinite(score) for score in scores):
                raise ValueError("Ranking scores must be finite numbers.")
            order = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
            relevant_total = sum(label > 0 for label in labels)
            top = order[:k]
            relevant_found = sum(labels[index] > 0 for index in top)
            precision_values.append(relevant_found / k)
            if relevant_total:
                recall_values.append(relevant_found / relevant_total)
            ndcg_values.append(_ndcg_at_k(labels, scores, k))
        metrics[f"precision@{k}"] = round(float(np.mean(precision_values)), 4)
        metrics[f"recall@{k}"] = round(
            float(np.mean(recall_values)) if recall_values else 0.0, 4
        )
        metrics[f"ndcg@{k}"] = round(float(np.mean(ndcg_values)), 4)
    return metrics


def _ndcg_at_k(labels: list[int], scores: list[float], k: int) -> float:
    try:
        from sklearn.metrics import ndcg_score

        return float(
            ndcg_score(
                np.asarray([labels], dtype=float),
                np.asarray([scores], dtype=float),
                k=min(k, len(labels)),
            )
        )
    except (ImportError, OSError):
        pass
    ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    ideal = sorted(range(len(labels)), key=lambda index: labels[index], reverse=True)
    dcg = sum(
        (2**labels[index] - 1) / np.log2(position + 2)
        for position, index in enumerate(ranked[:k])
    )
    ideal_dcg = sum(
        (2**labels[index] - 1) / np.log2(position + 2)
        for position, index in enumerate(ideal[:k])
    )
    return float(dcg / ideal_dcg) if ideal_dcg else 0.0


def evaluate_labeled_dataset(
    dataset_path: Path = DEFAULT_DATASET,
    settings: Settings | None = None,
    encoder: SentenceTransformerEncoder | None = None,
) -> dict[str, Any]:
    config = settings or get_settings()
    encoder = encoder or SentenceTransformerEncoder(config)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    query_records = dataset.get("queries")
    if not isinstance(query_records, list) or not query_records:
        raise ValueError("The evaluation dataset must contain a non-empty queries array.")

    comparisons: list[tuple[str, int, CandidateProfileData, JobProfileData, dict]] = []
    texts: list[str] = []
    for query in query_records:
        candidate = CandidateProfileData(
            skills=tuple(query["candidate"]["skills"]),
            experience_skills=tuple(query["candidate"]["experience_skills"]),
            experience_years=query["candidate"].get("experience_years"),
            work_evidence_count=query["candidate"].get("work_evidence_count", 0),
            education=tuple(query["candidate"].get("education", [])),
        )
        for job_data in query["jobs"]:
            job = JobProfileData(
                title=job_data["title"],
                required_skills=tuple(job_data.get("required_skills", [])),
                description_skills=tuple(job_data.get("description_skills", [])),
                minimum_experience_years=job_data.get("minimum_experience_years"),
                required_education=job_data.get("required_education"),
            )
            pair_texts = profile_embedding_texts(candidate, job)
            comparisons.append((query["id"], int(job_data["relevance"]), candidate, job, pair_texts))
            texts.extend(pair_texts.values())

    unique_texts = list(dict.fromkeys(texts))
    encoded = encoder.encode(unique_texts)
    if len(encoded) != len(unique_texts):
        raise ValueError("The embedding model returned an invalid evaluation result.")
    vectors_by_text = dict(zip(unique_texts, encoded))

    labels_by_query: dict[str, list[int]] = {}
    scores_by_query: dict[str, list[float]] = {}
    for query_id, relevance, candidate, job, pair_texts in comparisons:
        vector_aliases = {
            "candidate_skills": pair_texts.get(("candidate", "skills")),
            "candidate_experience": pair_texts.get(("candidate", "experience")),
            "job_description": pair_texts.get(("job", "description")),
            "job_requirements": pair_texts.get(("job", "requirements")),
        }
        vectors = {
            key: vectors_by_text[text]
            for key, text in vector_aliases.items()
            if text is not None
        }
        score = calculate_match(candidate, job, vectors, config)["total_score"]
        labels_by_query.setdefault(query_id, []).append(relevance)
        scores_by_query.setdefault(query_id, []).append(score)

    pair_count = sum(len(labels) for labels in labels_by_query.values())
    return {
        "dataset": dataset.get("name", dataset_path.name),
        "dataset_type": dataset.get("type", "unspecified"),
        "model": config.matching_embedding_model,
        "scoring_model_version": "careerlens-weighted-evidence-v1",
        "query_count": len(labels_by_query),
        "pair_count": pair_count,
        "metrics": ranking_metrics(labels_by_query, scores_by_query),
        "note": (
            "Offline ranking metrics over the supplied labeled pairs; they are not "
            "a production-quality or fairness certification."
        ),
    }
