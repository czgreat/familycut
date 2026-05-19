from io import BytesIO
import time
from types import SimpleNamespace
from datetime import datetime, timedelta, UTC

from fastapi.testclient import TestClient

from app.api import routes_nutrition, routes_settings
from app.main import app


def _login_admin(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "1099040334"},
    )
    assert response.status_code == 200
    return response.json()["tokens"]["access_token"]


def test_create_nutrition_draft_passes_hint_and_returns_estimated_grams(monkeypatch) -> None:
    def fake_resolve_ai_provider(db, household_id: str) -> object:
        return SimpleNamespace(household_id=household_id)

    def fake_analyze_food_image(image_path, provider, draft_type: str, hint_text: str | None = None) -> dict:
        assert image_path.exists()
        assert draft_type == "dish_estimate"
        assert hint_text == "达美乐意式肉酱披萨 9 寸"
        return {
            "food_name": "意式肉酱披萨",
            "raw_text": "按 9 寸薄底披萨整份估算",
            "estimated_grams": 420,
            "estimated_solid_grams": 420,
            "estimated_liquid_grams": 0,
            "estimated_scope": "solid_only",
            "portion_basis": "按 9 寸薄底披萨常见整份重量估算",
            "per_100g_kcal": 265,
            "per_100g_carb_g": 25,
            "per_100g_fat_g": 11,
            "per_100g_protein_g": 12,
            "per_100g_sodium_mg": 560,
            "confidence": 0.88,
            "provider_trace": {"provider": "test-double"},
        }

    monkeypatch.setattr(routes_nutrition, "resolve_ai_provider", fake_resolve_ai_provider)
    monkeypatch.setattr(routes_nutrition, "analyze_food_image", fake_analyze_food_image)

    with TestClient(app) as client:
        token = _login_admin(client)
        response = client.post(
            "/api/v1/nutrition/drafts",
            headers={"Authorization": f"Bearer {token}"},
            data={"draft_type": "dish_estimate", "hint_text": "达美乐意式肉酱披萨 9 寸"},
            files={"image": ("dish.jpg", BytesIO(b"fake-image-bytes"), "image/jpeg")},
        )

        assert response.status_code == 202
        draft_id = response.json()["id"]

        final_payload = None
        for _ in range(10):
            draft_response = client.get(
                f"/api/v1/nutrition/drafts/{draft_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert draft_response.status_code == 200
            final_payload = draft_response.json()
            if final_payload["status"] != "processing":
                break
            time.sleep(0.05)

    assert final_payload is not None
    assert final_payload["status"] == "ready"
    assert final_payload["food_name"] == "意式肉酱披萨"
    assert final_payload["hint_text"] == "达美乐意式肉酱披萨 9 寸"
    assert final_payload["estimated_grams"] == 420
    assert final_payload["estimated_solid_grams"] == 420
    assert final_payload["estimated_liquid_grams"] == 0
    assert final_payload["estimated_scope"] == "solid_only"
    assert final_payload["portion_basis"] == "按 9 寸薄底披萨常见整份重量估算"


def test_admin_ai_connection_test_endpoint(monkeypatch) -> None:
    def fake_probe_ai_provider(provider, prompt_text: str = "Reply with exactly OK"):
        assert provider.base_url == "http://localhost:23550/v1"
        assert provider.model_name == "gemini-3-flash-preview"
        return SimpleNamespace(
            ok=True,
            transport="openai_compat",
            detail="OK",
            model_name=provider.model_name,
            status_code=200,
        )

    monkeypatch.setattr(routes_settings, "probe_ai_provider", fake_probe_ai_provider)

    with TestClient(app) as client:
        token = _login_admin(client)
        response = client.post(
            "/api/v1/settings/tests/ai-connection",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "ai_base_url": "http://localhost:23550/v1",
                "ai_api_key": "sk-test",
                "ai_model_name": "gemini-3-flash-preview",
                "ai_timeout_sec": 60,
                "ai_proxy_enabled": False,
                "ai_proxy_url": None,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["transport"] == "openai_compat"
    assert payload["status_code"] == 200


def test_create_meal_defaults_consumed_at_to_current_time() -> None:
    before = datetime.now(UTC) - timedelta(seconds=5)

    with TestClient(app) as client:
        token = _login_admin(client)
        response = client.post(
            "/api/v1/meals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "meal_slot": "lunch",
                "food_name": "默认时间餐食",
                "actual_grams": 180,
                "kcal": 320,
                "carb_g": 25,
                "fat_g": 11,
                "protein_g": 20,
            },
        )

    assert response.status_code == 200
    consumed_at = datetime.fromisoformat(response.json()["consumed_at"])
    after = datetime.now(UTC) + timedelta(seconds=5)
    assert before <= consumed_at.astimezone(UTC) <= after
