from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_member
from app.db.session import get_db
from app.models import ExerciseEntry, Member
from app.schemas.nutrition import ExerciseEntryCreate, ExerciseEntryResponse
from app.services.tdee import estimate_exercise_kcal, latest_weight_kg


router = APIRouter(tags=["exercises"])


def _serialize(entry: ExerciseEntry, current_weight: float | None) -> ExerciseEntryResponse:
    return ExerciseEntryResponse(
        id=entry.id,
        exercise_type=entry.exercise_type,
        occurred_at=entry.occurred_at,
        distance_km=entry.distance_km,
        duration_min=entry.duration_min,
        estimated_kcal=estimate_exercise_kcal(entry, current_weight),
        note=entry.note,
    )


@router.post("/exercises", response_model=ExerciseEntryResponse)
def create_exercise(
    payload: ExerciseEntryCreate,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> ExerciseEntryResponse:
    entry = ExerciseEntry(member_id=current_member.id, **payload.model_dump(), estimated_kcal=None)
    entry.estimated_kcal = estimate_exercise_kcal(entry, latest_weight_kg(db, current_member.id))
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _serialize(entry, latest_weight_kg(db, current_member.id))


@router.get("/exercises", response_model=list[ExerciseEntryResponse])
def list_exercises(
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> list[ExerciseEntryResponse]:
    entries = (
        db.query(ExerciseEntry)
        .filter(ExerciseEntry.member_id == current_member.id)
        .order_by(ExerciseEntry.occurred_at.desc())
        .limit(30)
        .all()
    )
    current_weight = latest_weight_kg(db, current_member.id)
    return [_serialize(entry, current_weight) for entry in entries]
