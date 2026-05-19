from datetime import datetime

from pydantic import BaseModel, Field


class NutritionDraftResponse(BaseModel):
    id: str
    draft_type: str
    status: str
    food_name: str | None
    hint_text: str | None = None
    image_path: str
    image_url: str | None = None
    raw_text: str | None
    estimated_grams: float | None = None
    estimated_solid_grams: float | None = None
    estimated_liquid_grams: float | None = None
    estimated_scope: str | None = None
    portion_basis: str | None = None
    per_100g_kcal: float | None
    per_100g_carb_g: float | None
    per_100g_fat_g: float | None
    per_100g_protein_g: float | None
    per_100g_sodium_mg: float | None
    confidence: float | None
    error_message: str | None = None
    completed_at: datetime | None = None


class MealEntryCreate(BaseModel):
    draft_id: str | None = None
    meal_slot: str = Field(pattern="^(breakfast|lunch|dinner|snack)$")
    consumed_at: datetime | None = None
    food_name: str = Field(min_length=1, max_length=120)
    actual_grams: float = Field(gt=0, lt=5000)
    kcal: float = Field(ge=0)
    carb_g: float = Field(default=0, ge=0)
    fat_g: float = Field(default=0, ge=0)
    protein_g: float = Field(default=0, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)
    corrections: dict | None = None
    is_shared: bool = False


class MealEntryResponse(BaseModel):
    id: str
    draft_id: str | None = None
    draft_type: str | None = None
    meal_slot: str
    consumed_at: datetime
    food_name: str
    actual_grams: float
    kcal: float
    carb_g: float
    fat_g: float
    protein_g: float
    sodium_mg: float | None
    is_shared: bool
    source_image_path: str | None = None
    source_image_url: str | None = None
    source_food_name: str | None = None
    source_raw_text: str | None = None
    source_estimated_grams: float | None = None
    source_estimated_solid_grams: float | None = None
    source_estimated_liquid_grams: float | None = None
    source_estimated_scope: str | None = None
    source_portion_basis: str | None = None
    corrections: dict | None = None


class ExerciseEntryCreate(BaseModel):
    exercise_type: str = Field(
        pattern="^(mountain_bike_commute|walking|badminton|running_easy|running_tempo|running_fast|swimming|strength_training|custom)$"
    )
    occurred_at: datetime
    distance_km: float | None = Field(default=None, ge=0)
    duration_min: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=255)


class ExerciseEntryResponse(BaseModel):
    id: str
    exercise_type: str
    occurred_at: datetime
    distance_km: float | None
    duration_min: float | None
    estimated_kcal: float | None
    note: str | None
