from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uuid_str() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Household(TimestampMixin, Base):
    __tablename__ = "households"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    report_generate_hour: Mapped[int] = mapped_column(Integer, default=23)
    report_push_hour: Mapped[int] = mapped_column(Integer, default=8)

    members: Mapped[list["Member"]] = relationship(back_populates="household", cascade="all, delete-orphan")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="household", cascade="all, delete-orphan")


class Member(TimestampMixin, Base):
    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("username", name="uq_member_username"),
        UniqueConstraint("household_id", "username", name="uq_household_username"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(24), default="member")
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_factor: Mapped[float] = mapped_column(Float, default=1.2)
    goal_deficit_kcal: Mapped[int] = mapped_column(Integer, default=500)
    meal_slots: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["lunch", "dinner", "snack"])
    unit_preference: Mapped[str] = mapped_column(String(16), default="jin")
    share_by_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    household: Mapped["Household"] = relationship(back_populates="members")
    measurements: Mapped[list["MeasurementRecord"]] = relationship(back_populates="member", cascade="all, delete-orphan")
    exercises: Mapped[list["ExerciseEntry"]] = relationship(back_populates="member", cascade="all, delete-orphan")
    meals: Mapped[list["MealEntry"]] = relationship(back_populates="member", cascade="all, delete-orphan")
    nutrition_drafts: Mapped[list["NutritionDraft"]] = relationship(back_populates="member", cascade="all, delete-orphan")
    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="member", cascade="all, delete-orphan")
    reports: Mapped[list["DailyReport"]] = relationship(back_populates="member", cascade="all, delete-orphan")


class Invitation(TimestampMixin, Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(24), default="member")
    created_by_member_id: Mapped[str | None] = mapped_column(ForeignKey("members.id"), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_member_id: Mapped[str | None] = mapped_column(ForeignKey("members.id"), nullable=True)

    household: Mapped["Household"] = relationship(back_populates="invitations")


class MeasurementRecord(TimestampMixin, Base):
    __tablename__ = "measurement_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(24), default="manual")
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    impedance: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    external_dedup_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)

    member: Mapped["Member"] = relationship(back_populates="measurements")


class ExerciseEntry(TimestampMixin, Base):
    __tablename__ = "exercise_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    exercise_type: Mapped[str] = mapped_column(String(32), default="mountain_bike_commute")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    member: Mapped["Member"] = relationship(back_populates="exercises")


class NutritionDraft(TimestampMixin, Base):
    __tablename__ = "nutrition_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    draft_type: Mapped[str] = mapped_column(String(24), default="label")
    status: Mapped[str] = mapped_column(String(24), default="processing")
    food_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    hint_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_100g_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_100g_carb_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_100g_fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_100g_protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_100g_sodium_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_trace: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    member: Mapped["Member"] = relationship(back_populates="nutrition_drafts")


class MealEntry(TimestampMixin, Base):
    __tablename__ = "meal_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    draft_id: Mapped[str | None] = mapped_column(ForeignKey("nutrition_drafts.id"), nullable=True)
    meal_slot: Mapped[str] = mapped_column(String(24), nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    food_name: Mapped[str] = mapped_column(String(120), nullable=False)
    actual_grams: Mapped[float] = mapped_column(Float, nullable=False)
    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    carb_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    sodium_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)

    member: Mapped["Member"] = relationship(back_populates="meals")


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    media_type: Mapped[str] = mapped_column(String(24), default="selfie")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    original_path: Mapped[str] = mapped_column(String(255), nullable=False)
    preview_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    member: Mapped["Member"] = relationship(back_populates="media_assets")


class DailyReport(TimestampMixin, Base):
    __tablename__ = "daily_reports"
    __table_args__ = (UniqueConstraint("member_id", "report_date", name="uq_member_report_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="generated")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)

    member: Mapped["Member"] = relationship(back_populates="reports")


class NotificationEndpoint(TimestampMixin, Base):
    __tablename__ = "notification_endpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), nullable=False)
    endpoint_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    target_url: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AiProviderSetting(TimestampMixin, Base):
    __tablename__ = "ai_provider_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    vision_model: Mapped[str] = mapped_column(String(120), nullable=False)
    timeout_sec: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    proxy_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    proxy_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
