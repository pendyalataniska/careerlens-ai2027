from io import BytesIO

from docx import Document
import pytest
from pydantic import ValidationError

from app.api.v1 import matching as matching_api
from app.core.config import Settings
from app.services.matching import (
    SCORING_MODEL_VERSION,
    CandidateProfileData,
    JobProfileData,
    calculate_match,
)
from app.services.matching_evaluation import evaluate_labeled_dataset, ranking_metrics


def register_user(
    client,
    *,
    email: str,
    role: str,
    full_name: str,
    company_name: str | None = None,
) -> dict[str, str]:
    payload = {
        "email": email,
        "password": "secure-example-password",
        "role": role,
        "full_name": full_name,
    }
    if company_name:
        payload["company_name"] = company_name
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def make_resume() -> bytes:
    document = Document()
    document.add_heading("Skills", level=1)
    document.add_paragraph("Python, FastAPI, PostgreSQL")
    document.add_heading("Work Experience", level=1)
    document.add_paragraph(
        "Backend Engineer 2021-2025. Developed services with Python, FastAPI, PostgreSQL."
    )
    document.add_heading("Education", level=1)
    document.add_paragraph("Bachelor of Science in Computer Science")
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def fixed_embeddings(db, texts, settings=None):
    return {key: [1.0, 0.0] for key in texts}


def test_score_is_transparent_and_uses_explicit_requirements():
    candidate = CandidateProfileData(
        skills=("Python", "PostgreSQL"),
        experience_skills=("Python",),
        experience_years=2,
        work_evidence_count=1,
        education=("Bachelor of Science in Computer Science",),
    )
    job = JobProfileData(
        title="Backend Engineer",
        required_skills=("Python", "FastAPI"),
        description_skills=("Python", "FastAPI"),
        minimum_experience_years=4,
        required_education="Bachelor of Science",
    )
    embeddings = {
        "candidate_skills": [1.0, 0.0],
        "candidate_experience": [1.0, 0.0],
        "job_description": [1.0, 0.0],
        "job_requirements": [1.0, 0.0],
    }

    match = calculate_match(candidate, job, embeddings)

    assert match["scoring_model_version"] == SCORING_MODEL_VERSION
    assert match["score_details"]["matching_skills"] == ["Python"]
    assert match["score_details"]["missing_required_skills"] == ["FastAPI"]
    components = match["score_details"]["components"]
    assert components["skill_compatibility"]["score"] == 0.5
    assert components["relevant_experience"]["score"] == 0.5
    assert components["description_semantic_similarity"]["score"] == 1
    assert components["education_relevance"]["score"] == 1
    assert sum(
        component["effective_weight"] for component in components.values()
    ) == 1.0
    assert 0 <= match["total_score"] <= 100
    assert any("FastAPI" in item for item in match["score_details"]["explanations"])


def test_education_only_scores_when_job_explicitly_requires_it():
    candidate = CandidateProfileData(
        skills=("Python",),
        experience_skills=(),
        experience_years=None,
        work_evidence_count=0,
        education=("Bachelor of Science",),
    )
    job_without_education_requirement = JobProfileData(
        title="Python Developer",
        required_skills=("Python",),
        description_skills=("Python",),
        minimum_experience_years=None,
        required_education=None,
    )
    match = calculate_match(
        candidate,
        job_without_education_requirement,
        {"candidate_skills": [1.0, 0.0], "job_description": [1.0, 0.0]},
    )
    assert "education_relevance" not in match["score_details"]["components"]


def test_ranking_metrics_are_computed_per_query():
    metrics = ranking_metrics(
        {"q1": [1, 0, 1], "q2": [0, 1, 0]},
        {"q1": [0.9, 0.8, 0.1], "q2": [0.9, 0.8, 0.1]},
    )
    assert metrics["precision@1"] == 0.5
    assert metrics["recall@1"] == 0.25
    assert metrics["precision@3"] == 0.5
    assert metrics["recall@3"] == 1.0
    assert 0 < metrics["ndcg@3"] <= 1


def test_scoring_weights_must_be_validated_to_sum_to_one():
    with pytest.raises(ValidationError, match="sum to 1"):
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            secret_key="test-signing-key-with-at-least-thirty-two-characters",
            matching_skill_weight=0.5,
            matching_experience_weight=0.3,
            matching_semantic_weight=0.3,
            matching_education_weight=0.1,
        )


class FixtureEncoder:
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [
            [1.0, 0.0] if "python" in text.casefold() else [0.0, 1.0]
            for text in texts
        ]


def test_labeled_dataset_evaluation_returns_ranking_report():
    report = evaluate_labeled_dataset(encoder=FixtureEncoder())
    assert report["query_count"] == 3
    assert report["pair_count"] == 9
    assert set(report["metrics"]) == {
        "precision@1",
        "recall@1",
        "ndcg@1",
        "precision@3",
        "recall@3",
        "ndcg@3",
    }
    assert all(0 <= score <= 1 for score in report["metrics"].values())
    assert report["dataset_type"] == "synthetic_curated_labels"


def test_matching_api_persists_explanation_and_enforces_candidate_ownership(
    client, monkeypatch, tmp_path
):
    settings = matching_api.get_settings().model_copy(
        update={"resume_storage_dir": tmp_path}
    )
    from app.api.v1 import resumes as resume_api

    monkeypatch.setattr(matching_api, "get_settings", lambda: settings)
    monkeypatch.setattr(resume_api, "get_settings", lambda: settings)
    monkeypatch.setattr(
        matching_api, "persist_profile_embeddings", fixed_embeddings
    )
    candidate_headers = register_user(
        client,
        email="matching-candidate@example.com",
        role="CANDIDATE",
        full_name="Casey Candidate",
    )
    uploaded = client.post(
        "/api/v1/resumes/upload",
        headers=candidate_headers,
        files={
            "file": (
                "candidate.docx",
                make_resume(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert uploaded.status_code == 201

    recruiter_headers = register_user(
        client,
        email="matching-recruiter@example.com",
        role="RECRUITER",
        full_name="Taylor Recruiter",
        company_name="Example",
    )
    matching_job = client.post(
        "/api/v1/jobs",
        headers=recruiter_headers,
        json={
            "title": "Python Backend Engineer",
            "description": "Build backend services using Python and FastAPI.",
            "required_skills": ["Python", "FastAPI"],
            "minimum_experience_years": 3,
            "required_education": "Bachelor of Science",
        },
    )
    unrelated_job = client.post(
        "/api/v1/jobs",
        headers=recruiter_headers,
        json={
            "title": "React Frontend Engineer",
            "description": "Build frontend applications using React and TypeScript.",
            "required_skills": ["React", "TypeScript"],
        },
    )
    assert matching_job.status_code == unrelated_job.status_code == 201

    analyzed = client.post(
        "/api/v1/matching/analyze",
        headers=candidate_headers,
        json={"job_id": matching_job.json()["id"]},
    )
    assert analyzed.status_code == 201, analyzed.text
    result = analyzed.json()
    assert result["total_score"] > 0
    assert result["score_details"]["matching_skills"] == ["FastAPI", "Python"]
    assert result["score_details"]["missing_required_skills"] == []
    assert result["score_details"]["score_completeness"] == "complete"
    assert "protected traits" in " ".join(
        result["score_details"]["explanations"]
    ).casefold()

    fetched = client.get(
        f"/api/v1/matching/{result['id']}", headers=candidate_headers
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == result["id"]

    recommendations = client.get(
        "/api/v1/matching/recommendations?limit=2", headers=candidate_headers
    )
    assert recommendations.status_code == 200, recommendations.text
    items = recommendations.json()["items"]
    assert len(items) == 2
    assert items[0]["job_id"] == matching_job.json()["id"]

    other_candidate_headers = register_user(
        client,
        email="another-matching-candidate@example.com",
        role="CANDIDATE",
        full_name="Another Candidate",
    )
    denied = client.get(
        f"/api/v1/matching/{result['id']}", headers=other_candidate_headers
    )
    assert denied.status_code == 404

    forbidden = client.post(
        "/api/v1/matching/analyze",
        headers=recruiter_headers,
        json={"job_id": matching_job.json()["id"]},
    )
    assert forbidden.status_code == 403
