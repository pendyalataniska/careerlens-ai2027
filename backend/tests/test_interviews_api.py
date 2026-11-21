from io import BytesIO

from docx import Document

from app.api.v1 import resumes as resume_api
from app.core.config import get_settings
from app.services import interview_preparation


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
    document.add_paragraph("Jordan Davis | jordan.private@example.com")
    document.add_heading("Skills", level=1)
    document.add_paragraph("Python, PostgreSQL")
    document.add_heading("Work Experience", level=1)
    document.add_paragraph("Backend developer. Built APIs with FastAPI.")
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def setup_candidate_and_job(client, monkeypatch, tmp_path, suffix: str):
    candidate_headers = register_user(client, f"interview-{suffix}@example.com")
    settings = get_settings().model_copy(update={"resume_storage_dir": tmp_path})
    monkeypatch.setattr(resume_api, "get_settings", lambda: settings)
    upload = client.post(
        "/api/v1/resumes/upload",
        headers=candidate_headers,
        files={"file": ("resume.docx", make_resume(), DOCX_CONTENT_TYPE)},
    )
    assert upload.status_code == 201
    recruiter_headers = register_user(
        client, f"recruiter-{suffix}@example.com", role="RECRUITER"
    )
    job = client.post(
        "/api/v1/jobs",
        headers=recruiter_headers,
        json={
            "title": "Python Backend Engineer",
            "description": "Build Python services and REST APIs for customers.",
            "required_skills": ["Python", "FastAPI"],
        },
    )
    assert job.status_code == 201
    return candidate_headers, recruiter_headers, job.json()


def generated_questions():
    return {
        "questions": [
            {
                "category": "TECHNICAL",
                "prompt": "How would you design a Python API endpoint?",
                "targeted_skills": ["Python"],
            },
            {
                "category": "HR",
                "prompt": "Describe how you communicate API tradeoffs to a team.",
                "targeted_skills": ["FastAPI"],
            },
        ]
    }


def evaluation():
    return {
        "relevance": {"score": 4, "feedback": "You addressed the core question."},
        "technical_correctness": {
            "score": 3,
            "feedback": "Mention request validation and error handling.",
        },
        "clarity": {"score": 4, "feedback": "The answer was easy to follow."},
        "completeness": {"score": 3, "feedback": "Add a brief testing example."},
        "overall_feedback": "Good foundation; add implementation details.",
        "strengths": ["Clear explanation"],
        "areas_to_improve": ["Discuss validation"],
    }


def fake_gemini(prompt, settings=None):
    if "Return only JSON with keys relevance" in prompt:
        return evaluation()
    return generated_questions()


def test_candidate_can_generate_answer_and_review_interview_session(
    client, monkeypatch, tmp_path
):
    candidate_headers, _, job = setup_candidate_and_job(
        client, monkeypatch, tmp_path, "complete"
    )
    prompts = []

    def capture_prompt(prompt, settings=None):
        prompts.append(prompt)
        return fake_gemini(prompt, settings)

    monkeypatch.setattr(interview_preparation, "_gemini_json", capture_prompt)

    roles = client.get("/api/v1/interviews/roles", headers=candidate_headers)
    assert roles.status_code == 200
    assert roles.json()[0]["id"] == job["id"]

    created = client.post(
        "/api/v1/interviews/sessions",
        headers=candidate_headers,
        json={"job_id": job["id"], "technical_questions": 1, "hr_questions": 1},
    )
    assert created.status_code == 201, created.text
    session = created.json()
    assert session["role_title"] == "Python Backend Engineer"
    assert [item["category"] for item in session["questions"]] == ["TECHNICAL", "HR"]
    assert session["average_score"] is None
    assert len(prompts) == 1
    assert "Python Backend Engineer" in prompts[0]
    assert "Python" in prompts[0] and "FastAPI" in prompts[0]
    assert "jordan.private@example.com" not in prompts[0]
    assert "Backend developer. Built APIs" not in prompts[0]

    question = session["questions"][0]
    answered = client.post(
        f"/api/v1/interviews/sessions/{session['id']}/questions/{question['id']}/answer",
        headers=candidate_headers,
        json={"answer": "I would validate the request, call a service, and return a response."},
    )
    assert answered.status_code == 200, answered.text
    assert "jordan.private@example.com" not in prompts[1]
    updated = answered.json()
    assert updated["answered_questions"] == 1
    assert updated["status"] == "IN_PROGRESS"
    assert updated["questions"][0]["evaluation"]["technical_correctness"]["score"] == 3
    assert "not an objective measure" in updated["score_disclaimer"]

    second = updated["questions"][1]
    completed = client.post(
        f"/api/v1/interviews/sessions/{session['id']}/questions/{second['id']}/answer",
        headers=candidate_headers,
        json={"answer": "I explain tradeoffs with examples and invite team feedback."},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["average_score"] == 3.5

    analytics = client.get("/api/v1/interviews/analytics", headers=candidate_headers)
    assert analytics.status_code == 200
    assert analytics.json()["total_sessions"] == 1
    assert analytics.json()["completed_sessions"] == 1
    assert analytics.json()["answered_questions"] == 2
    assert analytics.json()["criterion_averages"]["clarity"] == 4
    assert "employability" in analytics.json()["disclaimer"]

    session_list = client.get(
        "/api/v1/interviews/sessions", headers=candidate_headers
    )
    assert len(session_list.json()["items"]) == 1


def test_interview_sessions_are_candidate_owned_and_role_protected(
    client, monkeypatch, tmp_path
):
    candidate_headers, recruiter_headers, job = setup_candidate_and_job(
        client, monkeypatch, tmp_path, "ownership"
    )
    monkeypatch.setattr(interview_preparation, "_gemini_json", fake_gemini)
    created = client.post(
        "/api/v1/interviews/sessions",
        headers=candidate_headers,
        json={"job_id": job["id"], "technical_questions": 1, "hr_questions": 1},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    other_candidate = register_user(client, "interview-other@example.com")
    assert client.get(
        f"/api/v1/interviews/sessions/{session_id}", headers=other_candidate
    ).status_code == 404
    assert client.get(
        "/api/v1/interviews/analytics", headers=recruiter_headers
    ).status_code == 403
    assert client.get(
        "/api/v1/interviews/roles"
    ).status_code == 401


def test_gemini_configuration_and_malformed_questions_fail_explicitly(
    client, monkeypatch, tmp_path
):
    candidate_headers, _, job = setup_candidate_and_job(
        client, monkeypatch, tmp_path, "provider"
    )
    unavailable = client.post(
        "/api/v1/interviews/sessions",
        headers=candidate_headers,
        json={"job_id": job["id"], "technical_questions": 1, "hr_questions": 1},
    )
    assert unavailable.status_code == 503
    assert "GEMINI_API_KEY" in unavailable.json()["detail"]

    monkeypatch.setattr(
        interview_preparation,
        "_gemini_json",
        lambda prompt, settings=None: {"questions": []},
    )
    malformed = client.post(
        "/api/v1/interviews/sessions",
        headers=candidate_headers,
        json={"job_id": job["id"], "technical_questions": 1, "hr_questions": 1},
    )
    assert malformed.status_code == 502

    invalid_counts = client.post(
        "/api/v1/interviews/sessions",
        headers=candidate_headers,
        json={"job_id": job["id"], "technical_questions": 0, "hr_questions": 1},
    )
    assert invalid_counts.status_code == 422
