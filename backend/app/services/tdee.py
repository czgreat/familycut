from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExerciseEntry, MealEntry, MeasurementRecord, Member

SEDENTARY_ACTIVITY_FACTOR = 1.2
PROTEIN_TARGET_G_PER_KG = 1.6
FAT_TARGET_G_PER_KG = 0.8
MACRO_HIT_LOWER_RATIO = 0.9
MACRO_HIT_UPPER_RATIO = 1.1

EXERCISE_PRESETS = {
    "mountain_bike_commute": {"met": 6.8, "speed_kmh": 14.0},
    "walking": {"met": 3.3, "speed_kmh": 4.8},
    "badminton": {"met": 5.5, "speed_kmh": None},
    "running_easy": {"met": 7.0, "speed_kmh": 8.0},
    "running_tempo": {"met": 9.8, "speed_kmh": 10.5},
    "running_fast": {"met": 11.0, "speed_kmh": 12.0},
    "swimming": {"met": 8.0, "speed_kmh": None},
    "strength_training": {"met": 5.0, "speed_kmh": None},
    "custom": {"met": 4.0, "speed_kmh": None},
}


def calculate_age(birthdate: date | None, today: date | None = None) -> int | None:
    if not birthdate:
        return None
    today = today or date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def latest_weight_kg(db: Session, member_id: str, *, as_of: datetime | None = None) -> float | None:
    stmt = (
        select(MeasurementRecord)
        .where(MeasurementRecord.member_id == member_id)
        .order_by(MeasurementRecord.measured_at.desc())
    )
    if as_of is not None:
        stmt = stmt.where(MeasurementRecord.measured_at <= as_of)
    row = db.scalar(stmt.limit(1))
    if row is None:
        return None
    return round(row.weight_kg, 2)


def rolling_weight_kg(db: Session, member_id: str, days: int = 7) -> float | None:
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.scalars(
        select(MeasurementRecord)
        .where(MeasurementRecord.member_id == member_id, MeasurementRecord.measured_at >= since)
        .order_by(MeasurementRecord.measured_at.desc())
    ).all()
    if not rows:
        return None
    return round(mean(item.weight_kg for item in rows), 2)


def calculate_bmr(member: Member, weight_kg: float | None) -> float | None:
    if member.height_cm is None or weight_kg is None or member.sex is None:
        return None
    age = calculate_age(member.birthdate)
    if age is None:
        return None
    sex_adjustment = 5 if member.sex.lower() in {"male", "m", "男"} else -161
    return round(10 * weight_kg + 6.25 * member.height_cm - 5 * age + sex_adjustment, 2)


def calculate_tdee(member: Member, weight_kg: float | None) -> float | None:
    bmr = calculate_bmr(member, weight_kg)
    if bmr is None:
        return None
    return round(bmr * member.activity_factor, 2)


def calculate_goal_intake_kcal(member: Member, tdee: float | None) -> float | None:
    if tdee is None:
        return None
    return round(max(tdee - float(member.goal_deficit_kcal or 0), 0.0), 2)


def macro_targets(member: Member, weight_kg: float | None, tdee: float | None) -> dict[str, float] | None:
    target_intake_kcal = calculate_goal_intake_kcal(member, tdee)
    if target_intake_kcal is None or weight_kg is None or weight_kg <= 0:
        return None

    protein_g = max(weight_kg * PROTEIN_TARGET_G_PER_KG, 0.0)
    fat_g = max(weight_kg * FAT_TARGET_G_PER_KG, 0.0)
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    minimum_macro_kcal = protein_kcal + fat_kcal

    if minimum_macro_kcal > target_intake_kcal and minimum_macro_kcal > 0:
        scale = target_intake_kcal / minimum_macro_kcal
        protein_g *= scale
        fat_g *= scale
        protein_kcal = protein_g * 4
        fat_kcal = fat_g * 9

    carb_kcal = max(target_intake_kcal - protein_kcal - fat_kcal, 0.0)
    carb_g = carb_kcal / 4
    totals = {
        "kcal": round(target_intake_kcal, 2),
        "carb_g": round(carb_g, 2),
        "fat_g": round(fat_g, 2),
        "protein_g": round(protein_g, 2),
    }
    return {
        **totals,
        **macro_percentages(totals),
    }


def macro_progress(actual_totals: dict[str, float], targets: dict[str, float] | None) -> dict[str, object] | None:
    if targets is None:
        return None

    progress: dict[str, object] = {}
    all_hit = True
    for macro_name in ("carb", "fat", "protein"):
        key = f"{macro_name}_g"
        actual = round(float(actual_totals.get(key, 0.0) or 0.0), 2)
        target = round(float(targets.get(key, 0.0) or 0.0), 2)
        progress_pct = round(actual / target * 100, 1) if target > 0 else None
        lower_bound = target * MACRO_HIT_LOWER_RATIO
        upper_bound = target * MACRO_HIT_UPPER_RATIO
        if target <= 0:
            hit = None
            status = "unknown"
        elif actual < lower_bound:
            hit = False
            status = "low"
            all_hit = False
        elif actual > upper_bound:
            hit = False
            status = "high"
            all_hit = False
        else:
            hit = True
            status = "on_target"
        progress[macro_name] = {
            "actual_g": actual,
            "target_g": target,
            "progress_pct": progress_pct,
            "remaining_g": round(max(target - actual, 0.0), 2),
            "excess_g": round(max(actual - target, 0.0), 2),
            "actual_pct": macro_percentages(actual_totals).get(f"{macro_name}_pct", 0.0),
            "target_pct": targets.get(f"{macro_name}_pct", 0.0),
            "hit": hit,
            "status": status,
        }
    progress["all_hit"] = all_hit
    return progress


def estimate_exercise_kcal(entry: ExerciseEntry, weight_kg: float | None) -> float | None:
    if weight_kg is None:
        return None
    preset = EXERCISE_PRESETS.get(entry.exercise_type, EXERCISE_PRESETS["custom"])
    duration_hours = None
    if entry.duration_min is not None and entry.duration_min > 0:
        duration_hours = entry.duration_min / 60
    elif entry.distance_km is not None and entry.distance_km > 0 and preset["speed_kmh"] is not None:
        duration_hours = entry.distance_km / float(preset["speed_kmh"])
    if duration_hours is None:
        return entry.estimated_kcal
    return round(float(preset["met"]) * weight_kg * duration_hours, 2)


def exercise_totals(db: Session, member_id: str, target_date: date, weight_kg: float | None) -> tuple[float, list[dict[str, float | str | None]]]:
    start = datetime.combine(target_date, datetime.min.time())
    end = start + timedelta(days=1)
    entries = db.scalars(
        select(ExerciseEntry)
        .where(ExerciseEntry.member_id == member_id, ExerciseEntry.occurred_at >= start, ExerciseEntry.occurred_at < end)
        .order_by(ExerciseEntry.occurred_at.asc())
    ).all()
    cards: list[dict[str, float | str | None]] = []
    total = 0.0
    for entry in entries:
        estimated_kcal = estimate_exercise_kcal(entry, weight_kg)
        if estimated_kcal is not None:
            total += estimated_kcal
        cards.append(
            {
                "id": entry.id,
                "exercise_type": entry.exercise_type,
                "occurred_at": entry.occurred_at.isoformat(),
                "distance_km": entry.distance_km,
                "duration_min": entry.duration_min,
                "estimated_kcal": estimated_kcal,
                "note": entry.note,
            }
        )
    return round(total, 2), cards


def consumed_totals(db: Session, member_id: str, target_date: date) -> dict[str, float]:
    start = datetime.combine(target_date, datetime.min.time())
    end = start + timedelta(days=1)
    meals = db.scalars(
        select(MealEntry).where(MealEntry.member_id == member_id, MealEntry.consumed_at >= start, MealEntry.consumed_at < end)
    ).all()
    totals = {"kcal": 0.0, "carb_g": 0.0, "fat_g": 0.0, "protein_g": 0.0}
    for meal in meals:
        totals["kcal"] += meal.kcal
        totals["carb_g"] += meal.carb_g
        totals["fat_g"] += meal.fat_g
        totals["protein_g"] += meal.protein_g
    return {key: round(value, 2) for key, value in totals.items()}


def macro_percentages(totals: dict[str, float]) -> dict[str, float]:
    carb_kcal = totals["carb_g"] * 4
    fat_kcal = totals["fat_g"] * 9
    protein_kcal = totals["protein_g"] * 4
    total = carb_kcal + fat_kcal + protein_kcal
    if total == 0:
        return {"carb_pct": 0.0, "fat_pct": 0.0, "protein_pct": 0.0}
    return {
        "carb_pct": round(carb_kcal / total * 100, 1),
        "fat_pct": round(fat_kcal / total * 100, 1),
        "protein_pct": round(protein_kcal / total * 100, 1),
    }
