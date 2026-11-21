def test_readiness_endpoint_reports_service_state(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
