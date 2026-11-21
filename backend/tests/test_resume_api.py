from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import fitz
from docx import Document

from app.api.v1 import resumes as resume_api
from app.core.config import get_settings
from app.services.resume_storage import PrivateResumeStorage


DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def register_candidate(client, email="resume-candidate@example.com"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "secure-example-password",
            "role": "CANDIDATE",
            "full_name": "Jordan Davis",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def make_docx() -> bytes:
    document = Document()
    document.add_paragraph("Jordan Davis | jordan.private@example.com | +1 415 555 0134")
    document.add_heading("Skills", level=1)
    document.add_paragraph("Python, PostgreSQL, C++")
    document.add_heading("Education", level=1)
    document.add_paragraph("Bachelor of Science, Example University")
    document.add_heading("Work Experience", level=1)
    document.add_paragraph("Software Engineer at Example Corp (2021-2024)")
    document.add_heading("Projects", level=1)
    document.add_paragraph("Built an internal hiring platform.")
    document.add_heading("Certifications", level=1)
    document.add_paragraph("Cloud Fundamentals Certificate")
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def configure_storage(monkeypatch, tmp_path: Path):
    settings = get_settings().model_copy(update={"resume_storage_dir": tmp_path})
    monkeypatch.setattr(resume_api, "get_settings", lambda: settings)
    return settings


def test_upload_extracts_evidence_and_keeps_file_private(
    client, monkeypatch, tmp_path
):
    settings = configure_storage(monkeypatch, tmp_path)
    headers = register_candidate(client)
    document_bytes = make_docx()

    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("Jordan_resume.docx", document_bytes, DOCX_CONTENT_TYPE)},
    )

    assert response.status_code == 201
    uploaded = response.json()
    assert uploaded["extraction_status"] == "completed"
    assert uploaded["content_type"] == DOCX_CONTENT_TYPE
    assert uploaded["file_size_bytes"] == len(document_bytes)
    task_status = client.get(
        f"/api/v1/resumes/{uploaded['id']}/task",
        headers=headers,
    )
    assert task_status.status_code == 200
    assert task_status.json()["status"] == "completed"
    assert client.get("/api/v1/resumes", headers=headers).json()[0]["id"] == uploaded["id"]
    assert not {"file_name", "storage_key", "sha256_digest", "extracted_data"} & uploaded.keys()

    analysis_response = client.get(
        f"/api/v1/resumes/{uploaded['id']}/analysis", headers=headers
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert [skill["name"] for skill in analysis["skills"]] == [
        "Python",
        "PostgreSQL",
        "C++",
    ]
    assert analysis["education"][0]["source"] == "resume_text"
    assert "Example University" in analysis["education"][0]["text"]
    assert "Software Engineer" in analysis["work_experience"][0]["text"]
    assert "Built an internal hiring platform." in analysis["projects"][0]["text"]
    assert "Cloud Fundamentals Certificate" in analysis["certifications"][0]["text"]
    assert analysis["contact_information_redacted"] is True
    assert "jordan.private@example.com" not in analysis_response.text
    assert "+1 415 555 0134" not in analysis_response.text
    assert "Jordan_resume.docx" not in analysis_response.text
    assert str(settings.resume_storage_dir) not in analysis_response.text

    stored_file = next(tmp_path.glob("*.clrs"))
    encrypted_contents = stored_file.read_bytes()
    assert encrypted_contents.startswith(b"CLRS1")
    assert b"jordan.private@example.com" not in encrypted_contents
    assert document_bytes not in encrypted_contents
    assert PrivateResumeStorage(settings).read(
        UUID(uploaded["id"]), stored_file.name
    ) == document_bytes


def test_resume_access_is_candidate_owned_and_role_protected(
    client, monkeypatch, tmp_path
):
    configure_storage(monkeypatch, tmp_path)
    owner_headers = register_candidate(client, "owner@example.com")
    response = client.post(
        "/api/v1/resumes/upload",
        headers=owner_headers,
        files={"file": ("resume.docx", make_docx(), DOCX_CONTENT_TYPE)},
    )
    assert response.status_code == 201
    resume_id = response.json()["id"]

    other_headers = register_candidate(client, "other@example.com")
    assert client.get(
        f"/api/v1/resumes/{resume_id}", headers=other_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/resumes/{resume_id}/analysis", headers=other_headers
    ).status_code == 404

    recruiter_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "recruiter@example.com",
            "password": "secure-example-password",
            "role": "RECRUITER",
            "full_name": "Riley Recruiter",
            "company_name": "Example Studio",
        },
    )
    recruiter_headers = {
        "Authorization": f"Bearer {recruiter_response.json()['access_token']}"
    }
    assert client.get(
        f"/api/v1/resumes/{resume_id}", headers=recruiter_headers
    ).status_code == 403


def test_scanned_pdf_is_stored_without_inferred_facts(client, monkeypatch, tmp_path):
    configure_storage(monkeypatch, tmp_path)
    headers = register_candidate(client)
    document = fitz.open()
    page = document.new_page()
    image = fitz.Pixmap(fitz.csRGB, (0, 0, 16, 16))
    page.insert_image(page.rect, stream=image.tobytes("png"))
    contents = document.tobytes()
    document.close()

    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("scanned.pdf", contents, "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["extraction_status"] == "scanned"
    analysis = client.get(
        f"/api/v1/resumes/{response.json()['id']}/analysis", headers=headers
    ).json()
    assert analysis["skills"] == []
    assert analysis["education"] == []
    assert any("OCR is not configured" in item for item in analysis["limitations"])


def test_invalid_type_and_oversized_upload_are_rejected(
    client, monkeypatch, tmp_path
):
    settings = configure_storage(monkeypatch, tmp_path)
    headers = register_candidate(client)
    invalid = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", b"not a PDF", "application/pdf")},
    )
    assert invalid.status_code == 422
    corrupted = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={
            "file": (
                "broken.pdf",
                b"%PDF-1.7\nnot a parseable PDF",
                "application/pdf",
            )
        },
    )
    assert corrupted.status_code == 201
    assert corrupted.json()["extraction_status"] == "failed"
    failed_task = client.get(
        f"/api/v1/resumes/{corrupted.json()['id']}/task",
        headers=headers,
    ).json()
    assert failed_task["status"] == "failed"
    assert "could not be processed" in failed_task["limitations"][0]

    limited_settings = settings.model_copy(
        update={"resume_max_file_size_bytes": 1024}
    )
    monkeypatch.setattr(resume_api, "get_settings", lambda: limited_settings)
    oversized = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", b"%PDF-" + b"x" * 1024, "application/pdf")},
    )
    assert oversized.status_code == 413


def test_corrupted_docx_returns_validation_error(client):
    headers = register_candidate(client)
    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("broken.docx", b"not a DOCX zip", DOCX_CONTENT_TYPE)},
    )
    assert response.status_code == 422
    assert "password" not in response.text.casefold()


def test_empty_docx_is_accepted_with_no_text_status(client, monkeypatch, tmp_path):
    configure_storage(monkeypatch, tmp_path)
    headers = register_candidate(client)
    document = Document()
    stream = BytesIO()
    document.save(stream)

    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("empty.docx", stream.getvalue(), DOCX_CONTENT_TYPE)},
    )
    assert response.status_code == 201
    assert response.json()["extraction_status"] == "no_text"


def test_contact_metadata_encryption_is_authenticated():
    storage = PrivateResumeStorage()
    resume_id = uuid4()
    contact_json = b'{"emails":["candidate@example.com"]}'
    encrypted = storage.encrypt_metadata(resume_id, contact_json)

    assert "candidate@example.com" not in encrypted
    assert storage.decrypt_metadata(resume_id, encrypted) == contact_json
