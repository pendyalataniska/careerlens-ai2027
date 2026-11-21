from io import BytesIO

from docx import Document

from app.api.v1 import resumes as resume_api
from app.core.config import get_settings


DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def register_user(client, email: str, role: str = "CANDIDATE") -> dict[str, str]:
    payload = {
        "email": email,
        "password": "secure-example-password",
        "role": role,
        "full_name": "Jordan Davis",
    }
    if role == "RECRUITER":
        payload["company_name"] = "Example Studio"
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def make_resume() -> bytes:
    document = Document()
    document.add_heading("Skills", level=1)
    document.add_paragraph("Python, PostgreSQL")
    document.add_heading("Work Experience", level=1)
    document.add_paragraph(
        "Software Engineer (2021-2024). Built backend services using FastAPI and Docker."
    )
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def add_resume(client, headers, monkeypatch, tmp_path):
    settings = get_settings().model_copy(update={"resume_storage_dir": tmp_path})
    monkeypatch.setattr(resume_api, "get_settings", lambda: settings)
    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.docx", make_resume(), DOCX_CONTENT_TYPE)},
    )
    assert response.status_code == 201, response.text


def create_job(client, recruiter_headers, title: str, skills: list[str]):
    return client.post(
        "/api/v1/jobs",
        headers=recruiter_headers,
        json={
            "title": title,
            "description": f"Build software with {', '.join(skills)} for customers.",
            "required_skills": skills,
        },
    )


def test_skill_gap_analysis_uses_evidence_and_learning_activity_is_owned(
    client, monkeypatch, tmp_path
):
    candidate_headers = register_user(client, "skill-candidate@example.com")
    add_resume(client, candidate_headers, monkeypatch, tmp_path)
    recruiter_headers = register_user(
        client, "skill-recruiter@example.com", role="RECRUITER"
    )
    job = create_job(
        client,
        recruiter_headers,
        "Backend Engineer",
        ["Python", "FastAPI", "React"],
    )
    assert job.status_code == 201

    analysis_response = client.get(
        f"/api/v1/skill-gaps/analysis?job_id={job.json()['id']}",
        headers=candidate_headers,
    )
    assert analysis_response.status_code == 200, analysis_response.text
    analysis = analysis_response.json()
    assert [entry["skill"] for entry in analysis["strong_matches"]] == ["Python"]
    assert [entry["skill"] for entry in analysis["partial_matches"]] == ["FastAPI"]
    assert [entry["skill"] for entry in analysis["missing_skills"]] == ["React"]
    assert analysis["partial_matches"][0]["learning_progress"] == 0
    assert analysis["missing_skills"][0]["resources"][0]["provider"] == "React"

    resource = analysis["missing_skills"][0]["resources"][0]
    started = client.post(
        "/api/v1/skill-gaps/activities",
        headers=candidate_headers,
        json={
            "skill": "React",
            "resource_id": resource["id"],
            "status": "IN_PROGRESS",
        },
    )
    assert started.status_code == 201, started.text
    assert started.json()["status"] == "IN_PROGRESS"

    refreshed = client.get(
        f"/api/v1/skill-gaps/analysis?job_id={job.json()['id']}",
        headers=candidate_headers,
    )
    assert refreshed.json()["missing_skills"][0]["learning_progress"] == 50
    activity_id = started.json()["id"]
    completed = client.patch(
        f"/api/v1/skill-gaps/activities/{activity_id}",
        headers=candidate_headers,
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None
    assert client.get(
        f"/api/v1/skill-gaps/activities", headers=candidate_headers
    ).json()[0]["status"] == "COMPLETED"

    other_candidate = register_user(client, "skill-other@example.com")
    assert client.patch(
        f"/api/v1/skill-gaps/activities/{activity_id}",
        headers=other_candidate,
        json={"status": "PLANNED"},
    ).status_code == 404


def test_learning_resource_validation_and_role_protection(
    client, monkeypatch, tmp_path
):
    candidate_headers = register_user(client, "resource-candidate@example.com")
    add_resume(client, candidate_headers, monkeypatch, tmp_path)
    invalid_resource = client.post(
        "/api/v1/skill-gaps/activities",
        headers=candidate_headers,
        json={
            "skill": "Python",
            "resource_id": "unverified-resource",
            "status": "PLANNED",
        },
    )
    assert invalid_resource.status_code == 422

    recruiter_headers = register_user(
        client, "resource-recruiter@example.com", role="RECRUITER"
    )
    assert client.get(
        "/api/v1/skill-gaps/activities", headers=recruiter_headers
    ).status_code == 403


def test_related_jobs_only_returns_active_listings_with_explicit_overlap(
    client, monkeypatch, tmp_path
):
    candidate_headers = register_user(client, "related-candidate@example.com")
    add_resume(client, candidate_headers, monkeypatch, tmp_path)
    recruiter_headers = register_user(
        client, "related-recruiter@example.com", role="RECRUITER"
    )
    matching = create_job(
        client, recruiter_headers, "Python Platform Engineer", ["Python", "Docker"]
    )
    unrelated = create_job(
        client, recruiter_headers, "Frontend Engineer", ["React", "TypeScript"]
    )

    response = client.get(
        "/api/v1/skill-gaps/related-jobs", headers=candidate_headers
    )
    assert response.status_code == 200, response.text
    assert [item["job_id"] for item in response.json()["items"]] == [
        matching.json()["id"]
    ]
    assert unrelated.json()["id"] not in {
        item["job_id"] for item in response.json()["items"]
    }
