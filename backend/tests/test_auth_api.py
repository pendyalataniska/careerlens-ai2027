def register_candidate(client, email="candidate@example.com"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "secure-example-password",
            "role": "CANDIDATE",
            "full_name": "Jordan Davis",
        },
    )


def register_recruiter(client, email="recruiter@example.com"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "secure-example-password",
            "role": "RECRUITER",
            "full_name": "Riley Recruiter",
            "company_name": "Example Studio",
        },
    )


def test_registration_hashes_password_and_returns_token(client):
    response = register_candidate(client)

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["role"] == "CANDIDATE"
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert "password" not in payload
    assert "hashed_password" not in payload

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    profile = client.get("/api/v1/candidates/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["first_name"] == "Jordan"
    assert profile.json()["last_name"] == "Davis"
    assert "resumes" not in profile.json()
    assert "hashed_password" not in profile.text


def test_duplicate_registration_and_invalid_login_are_rejected(client):
    assert register_candidate(client).status_code == 201
    duplicate = register_candidate(client)
    assert duplicate.status_code == 409

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@example.com", "password": "incorrect-password"},
    )
    assert invalid_login.status_code == 401
    assert invalid_login.json()["detail"] == "Invalid email or password."


def test_login_and_current_user(client):
    assert register_candidate(client).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "CANDIDATE@example.com", "password": "secure-example-password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    current_user = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "candidate@example.com"


def test_protected_route_rejects_missing_invalid_and_wrong_role(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-valid-token"},
        ).status_code
        == 401
    )

    recruiter = register_recruiter(client).json()
    headers = {"Authorization": f"Bearer {recruiter['access_token']}"}
    assert client.get("/api/v1/candidates/profile", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v1/jobs",
            headers=headers,
            json={
                "title": "Product Designer",
                "description": "Work with a cross-functional team to build great products.",
            },
        ).status_code
        == 201
    )

    candidate = register_candidate(client).json()
    candidate_headers = {"Authorization": f"Bearer {candidate['access_token']}"}
    denied = client.post(
        "/api/v1/jobs",
        headers=candidate_headers,
        json={
            "title": "Product Designer",
            "description": "Work with a cross-functional team to build great products.",
        },
    )
    assert denied.status_code == 403


def test_candidate_profile_update_and_job_listing(client):
    candidate = register_candidate(client).json()
    candidate_headers = {"Authorization": f"Bearer {candidate['access_token']}"}
    update = client.put(
        "/api/v1/candidates/profile",
        headers=candidate_headers,
        json={"headline": "Product designer", "location": "Remote"},
    )
    assert update.status_code == 200
    assert update.json()["headline"] == "Product designer"
    assert update.json()["location"] == "Remote"

    null_name = client.put(
        "/api/v1/candidates/profile",
        headers=candidate_headers,
        json={"full_name": None},
    )
    assert null_name.status_code == 200
    assert null_name.json()["first_name"] == "Jordan"

    recruiter = register_recruiter(client).json()
    recruiter_headers = {"Authorization": f"Bearer {recruiter['access_token']}"}
    created_job = client.post(
        "/api/v1/jobs",
        headers=recruiter_headers,
        json={
            "title": "Senior Product Designer",
            "description": "Design accessible product experiences with our growing team.",
            "location": "Remote",
            "employment_type": "Full-time",
        },
    )
    assert created_job.status_code == 201
    job_payload = created_job.json()
    assert job_payload["company_name"] == "Example Studio"
    assert "recruiter_id" not in job_payload

    listing = client.get("/api/v1/jobs?q=Product&location=remote")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == job_payload["id"]

    details = client.get(f"/api/v1/jobs/{job_payload['id']}")
    assert details.status_code == 200
    assert details.json()["title"] == "Senior Product Designer"


def test_candidate_dashboard_contains_only_real_account_data(client):
    candidate = register_candidate(client).json()
    headers = {"Authorization": f"Bearer {candidate['access_token']}"}

    response = client.get("/api/v1/candidates/dashboard", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["user"]["email"] == "candidate@example.com"
    assert data["latest_resume_id"] is None
    assert data["resume_status"] is None
    assert data["skills"] == []
    assert data["matches"] == []
    assert data["interview_sessions"] == 0
    assert data["completed_interviews"] == 0
    assert "not hiring probabilities" in data["disclaimer"]


def test_recruiter_can_list_only_own_jobs(client):
    first = register_recruiter(client, "first-recruiter@example.com").json()
    second = register_recruiter(client, "second-recruiter@example.com").json()
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    job_payload = {
        "title": "Product Designer",
        "description": "Work with a cross-functional team to build great products.",
    }

    own_job = client.post("/api/v1/jobs", headers=first_headers, json=job_payload)
    other_job = client.post("/api/v1/jobs", headers=second_headers, json=job_payload)
    assert own_job.status_code == 201
    assert other_job.status_code == 201

    response = client.get("/api/v1/jobs/mine", headers=first_headers)

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == own_job.json()["id"]
    assert client.get(
        "/api/v1/jobs/mine",
        headers={
            "Authorization": (
                "Bearer "
                f"{register_candidate(client).json()['access_token']}"
            )
        },
    ).status_code == 403


def test_validation_error_does_not_echo_password(client):
    password = "do-not-return-this-password"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bad",
            "password": password,
            "role": "CANDIDATE",
            "full_name": "Jordan Davis",
        },
    )
    assert response.status_code == 422
    assert password not in response.text
