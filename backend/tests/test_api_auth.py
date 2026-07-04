from __future__ import annotations


def test_register_login_me_refresh_flow(client):
    # register
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "password123", "full_name": "Flow"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "flow@example.com"

    # duplicate register
    response = client.post(
        "/api/v1/auth/register", json={"email": "flow@example.com", "password": "password123"}
    )
    assert response.status_code == 409

    # login
    response = client.post("/api/v1/auth/login", json={"email": "flow@example.com", "password": "password123"})
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    # me
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200

    # refresh
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["access_token"]

    # an access token must not work as a refresh token
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "password123"})
    response = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-password"})
    assert response.status_code == 401


def test_protected_routes_require_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/leads").status_code == 401
    assert client.get("/api/v1/campaigns").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_health_is_public(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
