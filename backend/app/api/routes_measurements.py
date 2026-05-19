from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_member
from app.db.session import get_db
from app.models import MeasurementRecord, Member
from app.schemas.measurement import HaMeasurementWebhook, MeasurementCreate, MeasurementResponse


router = APIRouter(tags=["measurements"])


def _serialize(record: MeasurementRecord) -> MeasurementResponse:
    return MeasurementResponse(
        id=record.id,
        source=record.source,
        measured_at=record.measured_at,
        weight_kg=record.weight_kg,
        body_fat_pct=record.body_fat_pct,
        impedance=record.impedance,
        note=record.note,
    )


@router.post("/measurements", response_model=MeasurementResponse)
def create_measurement(
    payload: MeasurementCreate,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> MeasurementResponse:
    record = MeasurementRecord(member_id=current_member.id, source="manual", **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize(record)


@router.get("/measurements", response_model=list[MeasurementResponse])
def list_measurements(
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> list[MeasurementResponse]:
    rows = db.scalars(
        select(MeasurementRecord)
        .where(MeasurementRecord.member_id == current_member.id)
        .order_by(MeasurementRecord.measured_at.desc())
        .limit(30)
    ).all()
    return [_serialize(row) for row in rows]


@router.post("/integrations/ha/measurements", response_model=MeasurementResponse)
def ingest_ha_measurement(payload: HaMeasurementWebhook, db: Session = Depends(get_db)) -> MeasurementResponse:
    member = db.scalar(
        select(Member).where(Member.household_id == payload.household_id, Member.username == payload.member_username)
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在")
    record = MeasurementRecord(
        member_id=member.id,
        source="ha_webhook",
        measured_at=payload.measured_at,
        weight_kg=payload.weight_kg,
        body_fat_pct=payload.body_fat_pct,
        impedance=payload.impedance,
        raw_payload=payload.raw_payload,
        external_dedup_key=payload.dedup_key,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(MeasurementRecord).where(MeasurementRecord.external_dedup_key == payload.dedup_key))
        if not existing:
            raise
        return _serialize(existing)
    db.refresh(record)
    return _serialize(record)
