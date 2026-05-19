from datetime import datetime

from pydantic import BaseModel, Field


class MeasurementCreate(BaseModel):
    measured_at: datetime
    weight_kg: float = Field(gt=0, lt=500)
    body_fat_pct: float | None = Field(default=None, ge=0, le=100)
    impedance: float | None = None
    note: str | None = Field(default=None, max_length=255)


class MeasurementResponse(BaseModel):
    id: str
    source: str
    measured_at: datetime
    weight_kg: float
    body_fat_pct: float | None
    impedance: float | None
    note: str | None


class HaMeasurementWebhook(BaseModel):
    household_id: str
    member_username: str
    measured_at: datetime
    weight_kg: float = Field(gt=0, lt=500)
    body_fat_pct: float | None = Field(default=None, ge=0, le=100)
    impedance: float | None = None
    dedup_key: str
    raw_payload: dict | None = None
