from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_member
from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models import MealEntry, Member, NutritionDraft
from app.schemas.nutrition import MealEntryCreate, MealEntryResponse, NutritionDraftResponse
from app.services.ai import analyze_food_image, resolve_ai_provider


router = APIRouter(tags=["nutrition"])


def _draft_dir(member_id: str) -> Path:
    settings = get_settings()
    target = settings.media_root / "nutrition" / member_id
    target.mkdir(parents=True, exist_ok=True)
    return target


def _media_url(file_path: str | None) -> str | None:
    if not file_path:
        return None
    settings = get_settings()
    try:
        relative = Path(file_path).resolve().relative_to(settings.media_root.resolve())
    except ValueError:
        return None
    return f"/media-files/{relative.as_posix()}"


def _weight_estimation_from_trace(draft: NutritionDraft | None) -> dict[str, object | None]:
    provider_trace = draft.provider_trace if draft and isinstance(draft.provider_trace, dict) else {}
    weight_estimation = provider_trace.get("weight_estimation") if isinstance(provider_trace.get("weight_estimation"), dict) else {}
    solid_grams = weight_estimation.get("estimated_solid_grams")
    liquid_grams = weight_estimation.get("estimated_liquid_grams")
    estimated_grams = draft.estimated_grams if draft else None
    if estimated_grams is None:
        solid_value = float(solid_grams) if isinstance(solid_grams, (int, float)) else None
        liquid_value = float(liquid_grams) if isinstance(liquid_grams, (int, float)) else None
        if solid_value is not None or liquid_value is not None:
            estimated_grams = (solid_value or 0.0) + (liquid_value or 0.0)
    return {
        "estimated_grams": estimated_grams,
        "estimated_solid_grams": weight_estimation.get("estimated_solid_grams"),
        "estimated_liquid_grams": weight_estimation.get("estimated_liquid_grams"),
        "estimated_scope": weight_estimation.get("estimated_scope"),
        "portion_basis": weight_estimation.get("portion_basis"),
    }


def _serialize_draft(draft: NutritionDraft) -> NutritionDraftResponse:
    weight_estimation = _weight_estimation_from_trace(draft)
    return NutritionDraftResponse(
        id=draft.id,
        draft_type=draft.draft_type,
        status=draft.status,
        food_name=draft.food_name,
        hint_text=draft.hint_text,
        image_path=draft.image_path,
        image_url=_media_url(draft.image_path),
        raw_text=draft.raw_text,
        estimated_grams=draft.estimated_grams,
        estimated_solid_grams=weight_estimation["estimated_solid_grams"],
        estimated_liquid_grams=weight_estimation["estimated_liquid_grams"],
        estimated_scope=weight_estimation["estimated_scope"],
        portion_basis=weight_estimation["portion_basis"],
        per_100g_kcal=draft.per_100g_kcal,
        per_100g_carb_g=draft.per_100g_carb_g,
        per_100g_fat_g=draft.per_100g_fat_g,
        per_100g_protein_g=draft.per_100g_protein_g,
        per_100g_sodium_mg=draft.per_100g_sodium_mg,
        confidence=draft.confidence,
        error_message=draft.error_message,
        completed_at=draft.completed_at,
    )


def _serialize_meal(meal: MealEntry, db: Session) -> MealEntryResponse:
    draft = db.get(NutritionDraft, meal.draft_id) if meal.draft_id else None
    weight_estimation = _weight_estimation_from_trace(draft)
    return MealEntryResponse(
        id=meal.id,
        draft_id=meal.draft_id,
        draft_type=draft.draft_type if draft else None,
        meal_slot=meal.meal_slot,
        consumed_at=meal.consumed_at,
        food_name=meal.food_name,
        actual_grams=meal.actual_grams,
        kcal=meal.kcal,
        carb_g=meal.carb_g,
        fat_g=meal.fat_g,
        protein_g=meal.protein_g,
        sodium_mg=meal.sodium_mg,
        is_shared=meal.is_shared,
        source_image_path=draft.image_path if draft else None,
        source_image_url=_media_url(draft.image_path) if draft else None,
        source_food_name=draft.food_name if draft else None,
        source_raw_text=draft.raw_text if draft else None,
        source_estimated_grams=weight_estimation["estimated_grams"],
        source_estimated_solid_grams=weight_estimation["estimated_solid_grams"],
        source_estimated_liquid_grams=weight_estimation["estimated_liquid_grams"],
        source_estimated_scope=weight_estimation["estimated_scope"],
        source_portion_basis=weight_estimation["portion_basis"],
        corrections=meal.corrections,
    )


def _mark_draft_failed(draft: NutritionDraft, message: str) -> None:
    draft.status = "failed"
    draft.error_message = message[:255]
    draft.completed_at = datetime.now()


def _apply_draft_result(draft: NutritionDraft, extracted: dict) -> None:
    draft.status = "ready"
    draft.food_name = extracted.get("food_name")
    draft.raw_text = extracted.get("raw_text")
    draft.estimated_grams = extracted.get("estimated_grams")
    draft.per_100g_kcal = extracted.get("per_100g_kcal")
    draft.per_100g_carb_g = extracted.get("per_100g_carb_g")
    draft.per_100g_fat_g = extracted.get("per_100g_fat_g")
    draft.per_100g_protein_g = extracted.get("per_100g_protein_g")
    draft.per_100g_sodium_mg = extracted.get("per_100g_sodium_mg")
    draft.confidence = extracted.get("confidence")
    provider_trace = extracted.get("provider_trace") if isinstance(extracted.get("provider_trace"), dict) else {}
    provider_trace["weight_estimation"] = {
        "estimated_solid_grams": extracted.get("estimated_solid_grams"),
        "estimated_liquid_grams": extracted.get("estimated_liquid_grams"),
        "estimated_scope": extracted.get("estimated_scope"),
        "portion_basis": extracted.get("portion_basis"),
    }
    draft.provider_trace = provider_trace
    draft.error_message = None
    draft.completed_at = datetime.now()


def _process_nutrition_draft_async(draft_id: str, household_id: str) -> None:
    with SessionLocal() as db:
        draft = db.get(NutritionDraft, draft_id)
        if draft is None:
            return
        try:
            provider = resolve_ai_provider(db, household_id)
            extracted = analyze_food_image(Path(draft.image_path), provider, draft.draft_type, draft.hint_text)
            _apply_draft_result(draft, extracted)
        except HTTPException as error:
            _mark_draft_failed(draft, str(error.detail))
        except Exception:
            _mark_draft_failed(draft, "后台识别失败，请稍后重试。")
        db.add(draft)
        db.commit()


@router.post("/nutrition/drafts", response_model=NutritionDraftResponse, status_code=status.HTTP_202_ACCEPTED)
def create_nutrition_draft(
    background_tasks: BackgroundTasks,
    draft_type: str = Form(default="label"),
    hint_text: str | None = Form(default=None),
    image: UploadFile = File(...),
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> NutritionDraftResponse:
    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    file_path = _draft_dir(current_member.id) / f"{uuid4()}{suffix}"
    file_path.write_bytes(image.file.read())

    if draft_type not in {"label", "dish_estimate"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的餐食识别类型")
    draft = NutritionDraft(
        member_id=current_member.id,
        draft_type=draft_type,
        status="processing",
        hint_text=hint_text.strip() if hint_text and hint_text.strip() else None,
        image_path=str(file_path),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    background_tasks.add_task(_process_nutrition_draft_async, draft.id, current_member.household_id)
    return _serialize_draft(draft)


@router.get("/nutrition/drafts/{draft_id}", response_model=NutritionDraftResponse)
def get_nutrition_draft(
    draft_id: str,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> NutritionDraftResponse:
    draft = db.scalar(select(NutritionDraft).where(NutritionDraft.id == draft_id, NutritionDraft.member_id == current_member.id))
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="识别草稿不存在")
    return _serialize_draft(draft)


@router.post("/meals", response_model=MealEntryResponse)
def create_meal(
    payload: MealEntryCreate,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> MealEntryResponse:
    if payload.draft_id:
        draft = db.scalar(select(NutritionDraft).where(NutritionDraft.id == payload.draft_id, NutritionDraft.member_id == current_member.id))
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="识别草稿不存在")
    meal_payload = payload.model_dump()
    meal_payload["consumed_at"] = payload.consumed_at or datetime.now()
    meal = MealEntry(member_id=current_member.id, **meal_payload)
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return _serialize_meal(meal, db)


@router.get("/meals", response_model=list[MealEntryResponse])
def list_meals(
    target_date: date | None = None,
    limit: int = 60,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> list[MealEntryResponse]:
    stmt = select(MealEntry).where(MealEntry.member_id == current_member.id)
    if target_date is not None:
        start = datetime.combine(target_date, datetime.min.time())
        end = start + timedelta(days=1)
        stmt = stmt.where(MealEntry.consumed_at >= start, MealEntry.consumed_at < end)
    meals = db.scalars(stmt.order_by(MealEntry.consumed_at.desc()).limit(min(max(limit, 1), 120))).all()
    return [_serialize_meal(meal, db) for meal in meals]
