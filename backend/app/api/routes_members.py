from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_member, require_admin
from app.db.session import get_db
from app.models import DailyReport, ExerciseEntry, Invitation, MealEntry, MeasurementRecord, Member
from app.schemas.member import (
    ExerciseHistoryItem,
    InvitationCreateRequest,
    InvitationHistoryResponse,
    InvitationResponse,
    MeasurementHistoryItem,
    MemberDetailResponse,
    MealHistoryItem,
    MemberProfileResponse,
    MemberProfileUpdate,
    MemberSummaryResponse,
    ReportHistoryItem,
)
from app.services.auth import create_invitation


router = APIRouter(prefix="/members", tags=["members"])


def _serialize_member(member: Member) -> MemberProfileResponse:
    return MemberProfileResponse(
        id=member.id,
        household_id=member.household_id,
        username=member.username,
        display_name=member.display_name,
        role=member.role,
        sex=member.sex,
        birth_year=member.birthdate.year if member.birthdate else None,
        height_cm=member.height_cm,
        activity_factor=member.activity_factor,
        goal_deficit_kcal=member.goal_deficit_kcal,
        meal_slots=member.meal_slots,
        unit_preference=member.unit_preference,
        share_by_default=member.share_by_default,
    )


def _serialize_member_summary(member: Member, db: Session) -> MemberSummaryResponse:
    latest_measurement = db.scalar(
        select(MeasurementRecord)
        .where(MeasurementRecord.member_id == member.id)
        .order_by(MeasurementRecord.measured_at.desc())
    )
    latest_report_date = db.scalar(select(func.max(DailyReport.report_date)).where(DailyReport.member_id == member.id))

    return MemberSummaryResponse(
        id=member.id,
        username=member.username,
        display_name=member.display_name,
        role=member.role,
        height_cm=member.height_cm,
        activity_factor=member.activity_factor,
        goal_deficit_kcal=member.goal_deficit_kcal,
        meal_slots=member.meal_slots,
        share_by_default=member.share_by_default,
        measurement_count=db.scalar(select(func.count(MeasurementRecord.id)).where(MeasurementRecord.member_id == member.id)) or 0,
        meal_count=db.scalar(select(func.count(MealEntry.id)).where(MealEntry.member_id == member.id)) or 0,
        report_count=db.scalar(select(func.count(DailyReport.id)).where(DailyReport.member_id == member.id)) or 0,
        latest_weight_kg=latest_measurement.weight_kg if latest_measurement else None,
        latest_body_fat_pct=latest_measurement.body_fat_pct if latest_measurement else None,
        latest_measured_at=latest_measurement.measured_at.isoformat() if latest_measurement else None,
        latest_report_date=latest_report_date.isoformat() if latest_report_date else None,
        latest_exercise_kcal=db.scalar(
            select(ExerciseEntry.estimated_kcal)
            .where(ExerciseEntry.member_id == member.id)
            .order_by(ExerciseEntry.occurred_at.desc())
            .limit(1)
        ),
    )


def _serialize_invitation(invitation: Invitation) -> InvitationHistoryResponse:
    return InvitationHistoryResponse(
        id=invitation.id,
        code=invitation.code,
        role=invitation.role,
        created_at=invitation.created_at.isoformat(),
        used_at=invitation.used_at.isoformat() if invitation.used_at else None,
        used_by_member_id=invitation.used_by_member_id,
    )


def _serialize_member_detail(member: Member, db: Session) -> MemberDetailResponse:
    summary = _serialize_member_summary(member, db)
    recent_measurements = db.scalars(
        select(MeasurementRecord)
        .where(MeasurementRecord.member_id == member.id)
        .order_by(MeasurementRecord.measured_at.desc())
        .limit(7)
    ).all()
    recent_meals = db.scalars(
        select(MealEntry)
        .where(MealEntry.member_id == member.id)
        .order_by(MealEntry.consumed_at.desc())
        .limit(10)
    ).all()
    recent_exercises = db.scalars(
        select(ExerciseEntry)
        .where(ExerciseEntry.member_id == member.id)
        .order_by(ExerciseEntry.occurred_at.desc())
        .limit(10)
    ).all()
    recent_reports = db.scalars(
        select(DailyReport)
        .where(DailyReport.member_id == member.id)
        .order_by(DailyReport.report_date.desc())
        .limit(7)
    ).all()

    return MemberDetailResponse(
        **summary.model_dump(),
        recent_measurements=[
            MeasurementHistoryItem(
                measured_at=item.measured_at.isoformat(),
                weight_kg=item.weight_kg,
                body_fat_pct=item.body_fat_pct,
            )
            for item in recent_measurements
        ],
        recent_meals=[
            MealHistoryItem(
                consumed_at=item.consumed_at.isoformat(),
                meal_slot=item.meal_slot,
                food_name=item.food_name,
                actual_grams=item.actual_grams,
                kcal=item.kcal,
            )
            for item in recent_meals
        ],
        recent_exercises=[
            ExerciseHistoryItem(
                occurred_at=item.occurred_at.isoformat(),
                exercise_type=item.exercise_type,
                distance_km=item.distance_km,
                duration_min=item.duration_min,
                estimated_kcal=item.estimated_kcal,
                note=item.note,
            )
            for item in recent_exercises
        ],
        recent_reports=[
            ReportHistoryItem(
                report_date=item.report_date.isoformat(),
                deficit_kcal=item.payload.get("deficit_kcal") if isinstance(item.payload, dict) else None,
                deficit_hit=item.payload.get("deficit_hit") if isinstance(item.payload, dict) else None,
                carb_g=(item.payload.get("intake") or {}).get("carb_g") if isinstance(item.payload, dict) and isinstance(item.payload.get("intake"), dict) else None,
                fat_g=(item.payload.get("intake") or {}).get("fat_g") if isinstance(item.payload, dict) and isinstance(item.payload.get("intake"), dict) else None,
                protein_g=(item.payload.get("intake") or {}).get("protein_g") if isinstance(item.payload, dict) and isinstance(item.payload.get("intake"), dict) else None,
            )
            for item in recent_reports
        ],
    )


@router.get("/me", response_model=MemberProfileResponse)
def me(current_member: Member = Depends(get_current_member)) -> MemberProfileResponse:
    return _serialize_member(current_member)


@router.put("/me", response_model=MemberProfileResponse)
def update_me(
    payload: MemberProfileUpdate,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> MemberProfileResponse:
    updates = payload.model_dump(exclude_unset=True)
    if "sex" in updates and current_member.sex is not None and updates["sex"] != current_member.sex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="性别首次设置后不可修改")
    if "birth_year" in updates:
        target_year = updates["birth_year"]
        if current_member.birthdate is not None and target_year != current_member.birthdate.year:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="出生年份首次设置后不可修改")
        updates["birthdate"] = date(target_year, 1, 1) if target_year is not None else None
        updates.pop("birth_year", None)
    for field, value in updates.items():
        setattr(current_member, field, value)
    db.add(current_member)
    db.commit()
    db.refresh(current_member)
    return _serialize_member(current_member)


@router.get("", response_model=list[MemberProfileResponse])
def list_household_members(
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[MemberProfileResponse]:
    members = db.scalars(select(Member).where(Member.household_id == admin.household_id).order_by(Member.created_at.asc())).all()
    return [_serialize_member(member) for member in members]


@router.get("/summary", response_model=list[MemberSummaryResponse])
def list_household_member_summaries(
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[MemberSummaryResponse]:
    members = db.scalars(select(Member).where(Member.household_id == admin.household_id).order_by(Member.created_at.asc())).all()
    return [_serialize_member_summary(member, db) for member in members]


@router.get("/{member_id}/detail", response_model=MemberDetailResponse)
def get_household_member_detail(
    member_id: str,
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MemberDetailResponse:
    member = db.scalar(select(Member).where(Member.household_id == admin.household_id, Member.id == member_id))
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在")
    return _serialize_member_detail(member, db)


@router.post("/invitations", response_model=InvitationResponse)
def create_household_invitation(
    payload: InvitationCreateRequest,
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> InvitationResponse:
    invitation = create_invitation(db, admin.household_id, payload.role, admin.id)
    return InvitationResponse(code=invitation.code, role=invitation.role)


@router.get("/invitations", response_model=list[InvitationHistoryResponse])
def list_household_invitations(
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[InvitationHistoryResponse]:
    invitations = db.scalars(
        select(Invitation)
        .where(Invitation.household_id == admin.household_id)
        .order_by(Invitation.created_at.desc())
    ).all()
    return [_serialize_invitation(invitation) for invitation in invitations]
