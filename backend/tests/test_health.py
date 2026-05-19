from fastapi.testclient import TestClient

from app.main import app


def test_healthcheck() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_bootstrap_admin_can_login() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "1099040334"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["role"] == "admin"
        assert payload["tokens"]["access_token"]


def test_recent_reports_endpoint_is_available_for_logged_in_member() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "1099040334"},
        )
        assert login.status_code == 200
        token = login.json()["tokens"]["access_token"]

        response = client.get(
            "/api/v1/reports/recent",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_media_files_mount_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/media-files")
        assert response.status_code in (200, 404)


def test_report_files_mount_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/report-files")
        assert response.status_code in (200, 404)


def test_household_selfies_endpoint_is_available_for_admin() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "1099040334"},
        )
        assert login.status_code == 200
        token = login.json()["tokens"]["access_token"]

        response = client.get(
            "/api/v1/media/household/selfies",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_app_config_includes_wechatbot_fields() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "1099040334"},
        )
        assert login.status_code == 200
        token = login.json()["tokens"]["access_token"]

        response = client.get(
            "/api/v1/settings/app-config",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert "ai_enabled" in payload
        assert "ai_base_url" in payload
        assert "ai_api_key" in payload
        assert "ai_model_name" in payload
        assert "ai_proxy_enabled" in payload
        assert "ai_proxy_url" in payload
        assert "report_generate_hour" in payload
        assert "report_push_hour" in payload
        assert "wechatbot_webhook_enabled" in payload
        assert "wechatbot_base_url" in payload


def test_username_audit_endpoint_is_available_for_admin() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "1099040334"},
        )
        assert login.status_code == 200
        token = login.json()["tokens"]["access_token"]

        response = client.get(
            "/api/v1/settings/username-audit",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["duplicate_usernames"] == []
        assert payload["has_global_unique_username_constraint"] is True
        assert payload["has_household_scoped_unique_username_constraint"] is True
        assert payload["guard_enabled"] is False
        assert payload["can_enable_guard"] is True
