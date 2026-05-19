from datetime import date

from pydantic import BaseModel, Field


class MemberProfileResponse(BaseModel):
    id: str
    household_id: str
    username: str
    display_name: str
    role: str
    sex: str | None
    birth_year: int | None
    height_cm: float | None
    activity_factor: float
    goal_deficit_kcal: int
    meal_slots: list[str]
    unit_preference: str
    share_by_default: bool


class MemberProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    sex: str | None = Field(default=None, max_length=16)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    height_cm: float | None = None
    activity_factor: float | None = None
    goal_deficit_kcal: int | None = None
    meal_slots: list[str] | None = None
    unit_preference: str | None = Field(default=None, max_length=16)
    share_by_default: bool | None = None


class InvitationCreateRequest(BaseModel):
    role: str = "member"


class InvitationResponse(BaseModel):
    code: str
    role: str


class InvitationHistoryResponse(BaseModel):
    id: str
    code: str
    role: str
    created_at: str
    used_at: str | None
    used_by_member_id: str | None


class MemberSummaryResponse(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    height_cm: float | None
    activity_factor: float
    goal_deficit_kcal: int
    meal_slots: list[str]
    share_by_default: bool
    measurement_count: int
    meal_count: int
    report_count: int
    latest_weight_kg: float | None
    latest_body_fat_pct: float | None
    latest_measured_at: str | None
    latest_report_date: str | None
    latest_exercise_kcal: float | None = None


class MeasurementHistoryItem(BaseModel):
    measured_at: str
    weight_kg: float
    body_fat_pct: float | None


class MealHistoryItem(BaseModel):
    consumed_at: str
    meal_slot: str
    food_name: str
    actual_grams: float
    kcal: float


class ExerciseHistoryItem(BaseModel):
    occurred_at: str
    exercise_type: str
    distance_km: float | None
    duration_min: float | None
    estimated_kcal: float | None
    note: str | None


class ReportHistoryItem(BaseModel):
    report_date: str
    deficit_kcal: float | None
    deficit_hit: bool | None
    carb_g: float | None = None
    fat_g: float | None = None
    protein_g: float | None = None


class MemberDetailResponse(MemberSummaryResponse):
    recent_measurements: list[MeasurementHistoryItem]
    recent_meals: list[MealHistoryItem]
    recent_exercises: list[ExerciseHistoryItem]
    recent_reports: list[ReportHistoryItem]
