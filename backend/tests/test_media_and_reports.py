from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.core.config import get_settings
from app.main import app
from app.models import DailyReport, ExerciseEntry, MediaAsset, MealEntry, MeasurementRecord, Member, NutritionDraft
from app.services.reports import generate_daily_report, generate_periodic_report


def _login_admin(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "1099040334"},
    )
    assert response.status_code == 200
    return response.json()["tokens"]["access_token"]


def _write_image(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), color).save(path, format="JPEG")


def test_household_selfies_endpoint_returns_only_shared_assets(db_session) -> None:
    settings = get_settings()
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None

    shared_path = settings.media_root / "selfies" / admin.id / "shared.jpg"
    private_path = settings.media_root / "selfies" / admin.id / "private.jpg"
    _write_image(shared_path, "#449955")
    _write_image(private_path, "#995544")

    shared_asset = MediaAsset(
        member_id=admin.id,
        media_type="selfie",
        captured_at=datetime.now(),
        original_path=str(shared_path),
        is_shared=True,
        note="共享自拍",
    )
    private_asset = MediaAsset(
        member_id=admin.id,
        media_type="selfie",
        captured_at=datetime.now(),
        original_path=str(private_path),
        is_shared=False,
        note="私密自拍",
    )
    db_session.add_all([shared_asset, private_asset])
    db_session.commit()

    with TestClient(app) as client:
        token = _login_admin(client)
        response = client.get(
            "/api/v1/media/household/selfies",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [shared_asset.id]


def test_daily_report_payload_uses_only_shared_media(db_session) -> None:
    settings = get_settings()
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None

    shared_path = settings.media_root / "selfies" / admin.id / "report-shared.jpg"
    private_path = settings.media_root / "selfies" / admin.id / "report-private.jpg"
    _write_image(shared_path, "#227744")
    _write_image(private_path, "#772244")

    db_session.add_all(
        [
            MediaAsset(
                member_id=admin.id,
                media_type="selfie",
                captured_at=datetime.now(),
                original_path=str(shared_path),
                is_shared=True,
            ),
            MediaAsset(
                member_id=admin.id,
                media_type="selfie",
                captured_at=datetime.now(),
                original_path=str(private_path),
                is_shared=False,
            ),
        ]
    )
    db_session.commit()

    report = generate_daily_report(db_session, admin, date.today())
    payload = report.payload

    assert payload["shared_media_paths"] == [str(shared_path)]
    assert payload["shared_media_urls"] == [f"/media-files/selfies/{admin.id}/{shared_path.name}"]
    assert str(private_path) not in payload["shared_media_paths"]


def test_meal_list_includes_draft_image_and_food_name(db_session) -> None:
    settings = get_settings()
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None
    admin_id = admin.id

    source_path = settings.media_root / "nutrition" / admin_id / "meal-source.jpg"
    _write_image(source_path, "#556677")
    draft = NutritionDraft(
        member_id=admin_id,
        draft_type="dish_estimate",
        food_name="番茄牛肉饭",
        image_path=str(source_path),
        raw_text="估算番茄牛肉饭，每100g约160kcal",
        provider_trace={
            "provider": "test-double",
            "weight_estimation": {
                "estimated_solid_grams": 260,
                "estimated_liquid_grams": 60,
                "estimated_scope": "includes_liquid",
                "portion_basis": "按米饭 180g、牛肉番茄 80g、汤汁 60g 估算",
            },
        },
        per_100g_kcal=160,
        per_100g_carb_g=18,
        per_100g_fat_g=4,
        per_100g_protein_g=10,
        per_100g_sodium_mg=300,
        confidence=0.82,
    )
    db_session.add(draft)
    db_session.flush()

    meal = MealEntry(
        member_id=admin_id,
        draft_id=draft.id,
        meal_slot="lunch",
        consumed_at=datetime.now(),
        food_name="番茄牛肉饭",
        actual_grams=320,
        kcal=512,
        carb_g=57.6,
        fat_g=12.8,
        protein_g=32,
        sodium_mg=960,
        corrections={"draft_type": "dish_estimate"},
    )
    db_session.add(meal)
    db_session.commit()

    with TestClient(app) as client:
        token = _login_admin(client)
        response = client.get(
            "/api/v1/meals",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["draft_type"] == "dish_estimate"
    assert payload["source_food_name"] == "番茄牛肉饭"
    assert payload["source_image_url"] == f"/media-files/nutrition/{admin_id}/{source_path.name}"
    assert payload["source_estimated_grams"] == 320
    assert payload["source_estimated_solid_grams"] == 260
    assert payload["source_estimated_liquid_grams"] == 60
    assert payload["source_estimated_scope"] == "includes_liquid"
    assert payload["source_portion_basis"] == "按米饭 180g、牛肉番茄 80g、汤汁 60g 估算"


def test_daily_report_includes_exercise_kcal(db_session) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None
    admin.sex = "male"
    admin.birthdate = date(1990, 1, 1)
    admin.height_cm = 175
    db_session.add(admin)
    db_session.commit()
    db_session.add(
        MeasurementRecord(
            member_id=admin.id,
            source="manual",
            measured_at=datetime.now(),
            weight_kg=82,
            body_fat_pct=20,
        )
    )
    db_session.commit()

    db_session.add(
        ExerciseEntry(
            member_id=admin.id,
            exercise_type="mountain_bike_commute",
            occurred_at=datetime.now(),
            distance_km=7,
            duration_min=None,
            note="通勤骑车",
        )
    )
    db_session.commit()

    report = generate_daily_report(db_session, admin, date.today())
    payload = report.payload

    assert payload["exercise_kcal"] > 0
    assert payload["tdee"] >= payload["base_tdee"]
    assert payload["exercise_cards"][0]["exercise_type"] == "mountain_bike_commute"
    assert payload["goal_intake_kcal"] is not None
    assert payload["macro_target"]["protein_g"] > 0
    assert payload["macro_target"]["fat_g"] > 0
    assert payload["macro_target"]["carb_g"] >= 0
    assert payload["macro_status"]["protein"]["target_g"] == payload["macro_target"]["protein_g"]
    assert payload["macro_status"]["fat"]["target_g"] == payload["macro_target"]["fat_g"]
    assert payload["macro_status"]["carb"]["target_g"] == payload["macro_target"]["carb_g"]


def test_daily_report_macro_status_marks_out_of_target_intake(db_session) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None
    admin.sex = "male"
    admin.birthdate = date(1990, 1, 1)
    admin.height_cm = 175
    admin.activity_factor = 1.4
    db_session.add(admin)
    db_session.commit()

    db_session.add(
        MeasurementRecord(
            member_id=admin.id,
            source="manual",
            measured_at=datetime.now(),
            weight_kg=80,
            body_fat_pct=18,
        )
    )
    db_session.add(
        MealEntry(
            member_id=admin.id,
            meal_slot="dinner",
            consumed_at=datetime.now(),
            food_name="低蛋白高脂测试餐",
            actual_grams=260,
            kcal=880,
            carb_g=40,
            fat_g=60,
            protein_g=18,
            sodium_mg=900,
            corrections=None,
        )
    )
    db_session.commit()

    report = generate_daily_report(db_session, admin, date.today())
    payload = report.payload

    assert payload["macro_status"]["protein"]["status"] == "low"
    assert payload["macro_status"]["fat"]["status"] in {"high", "on_target"}
    assert payload["macro_status"]["carb"]["status"] in {"low", "on_target", "high"}
    assert payload["macro_status"]["all_hit"] is False


def test_daily_report_uses_latest_weight_before_report_date(db_session) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None
    admin.sex = "male"
    admin.birthdate = date(1990, 1, 1)
    admin.height_cm = 175
    db_session.add(admin)
    db_session.commit()

    db_session.add_all(
        [
            MeasurementRecord(
                member_id=admin.id,
                source="manual",
                measured_at=datetime.combine(date.today() - timedelta(days=2), datetime.min.time()),
                weight_kg=92,
                body_fat_pct=21,
            ),
            MeasurementRecord(
                member_id=admin.id,
                source="manual",
                measured_at=datetime.combine(date.today() - timedelta(days=1), datetime.min.time()),
                weight_kg=79,
                body_fat_pct=20,
            ),
        ]
    )
    db_session.commit()

    report = generate_daily_report(db_session, admin, date.today() - timedelta(days=1))
    payload = report.payload

    assert payload["weight_kg"] == 79
    assert payload["weight_source"] == "latest_measurement"


def test_periodic_report_includes_average_macro_grams(db_session) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None
    today = date.today()
    first_day = datetime.combine(today - timedelta(days=1), datetime.min.time())
    second_day = datetime.combine(today, datetime.min.time())

    db_session.add_all(
        [
            MealEntry(
                member_id=admin.id,
                meal_slot="lunch",
                consumed_at=first_day,
                food_name="鸡胸肉米饭",
                actual_grams=300,
                kcal=540,
                carb_g=60,
                fat_g=12,
                protein_g=42,
                sodium_mg=800,
                corrections=None,
            ),
            MealEntry(
                member_id=admin.id,
                meal_slot="dinner",
                consumed_at=second_day,
                food_name="牛肉蔬菜碗",
                actual_grams=320,
                kcal=500,
                carb_g=40,
                fat_g=18,
                protein_g=38,
                sodium_mg=760,
                corrections=None,
            ),
        ]
    )
    db_session.commit()

    report_payload = generate_periodic_report(
        db_session,
        admin,
        "weekly",
        today - timedelta(days=1),
        today,
    )

    assert report_payload["payload"]["avg_intake"]["carb_g"] == 50.0
    assert report_payload["payload"]["avg_intake"]["fat_g"] == 15.0
    assert report_payload["payload"]["avg_intake"]["protein_g"] == 40.0


def test_member_detail_recent_reports_include_macro_grams(db_session) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None
    today = date.today()
    db_session.add(
        DailyReport(
            member_id=admin.id,
            report_date=today,
            status="generated",
            payload={
                "deficit_kcal": 520,
                "deficit_hit": True,
                "intake": {"carb_g": 88.4, "fat_g": 22.1, "protein_g": 61.6},
            },
            image_path=None,
        )
    )
    db_session.commit()

    with TestClient(app) as client:
        token = _login_admin(client)
        response = client.get(
            f"/api/v1/members/{admin.id}/detail",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    recent_report = response.json()["recent_reports"][0]
    assert recent_report["carb_g"] == 88.4
    assert recent_report["fat_g"] == 22.1
    assert recent_report["protein_g"] == 61.6


def test_daily_report_renders_png_file(db_session) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None

    report = generate_daily_report(db_session, admin, date.today())

    assert report.image_path is not None
    image_path = Path(report.image_path)
    assert image_path.exists()
    assert image_path.stat().st_size > 0


def test_periodic_report_generates_image_payload(db_session) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None

    today = date.today()
    report_payload = generate_periodic_report(
        db_session,
        admin,
        "weekly",
        today - timedelta(days=6),
        today,
    )

    assert report_payload["image_path"] is not None
    image_path = Path(report_payload["image_path"])
    assert image_path.exists()
    assert image_path.stat().st_size > 0
