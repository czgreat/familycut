from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_member, require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models import MediaAsset, Member
from app.schemas.media import MediaAssetResponse, SelfieCompareRequest, SelfieCompareResponse


router = APIRouter(tags=["media"])


def _media_dir(member_id: str) -> Path:
    settings = get_settings()
    target = settings.media_root / "selfies" / member_id
    target.mkdir(parents=True, exist_ok=True)
    return target


def _compare_dir(member_id: str) -> Path:
    settings = get_settings()
    target = settings.media_root / "comparisons" / member_id
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


def _serialize_media(asset: MediaAsset) -> MediaAssetResponse:
    return MediaAssetResponse(
        id=asset.id,
        media_type=asset.media_type,
        captured_at=asset.captured_at,
        original_path=asset.original_path,
        preview_path=asset.preview_path,
        original_url=_media_url(asset.original_path),
        preview_url=_media_url(asset.preview_path),
        is_shared=asset.is_shared,
        note=asset.note,
    )


def _build_preview(source: Path) -> Path:
    preview_path = source.with_name(f"{source.stem}_preview.jpg")
    with Image.open(source) as image:
        preview = image.copy()
        preview.thumbnail((1080, 1080))
        preview.convert("RGB").save(preview_path, format="JPEG", quality=88)
    return preview_path


def _build_compare_gif(first_path: Path, second_path: Path, target_path: Path) -> Path:
    frames: list[Image.Image] = []
    for source in (first_path, second_path):
        with Image.open(source) as image:
            frame = image.convert("RGB")
            frame.thumbnail((720, 720))
            canvas = Image.new("RGB", (720, 720), "#F4E7D7")
            offset_x = (720 - frame.width) // 2
            offset_y = (720 - frame.height) // 2
            canvas.paste(frame, (offset_x, offset_y))
            frames.append(canvas)
    frames[0].save(
        target_path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=900,
        loop=0,
    )
    return target_path


@router.post("/media/selfies", response_model=MediaAssetResponse)
def upload_selfie(
    captured_at: str = Form(...),
    is_shared: bool = Form(False),
    note: str | None = Form(default=None),
    image: UploadFile = File(...),
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> MediaAssetResponse:
    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    original_path = _media_dir(current_member.id) / f"{uuid4()}{suffix}"
    original_path.write_bytes(image.file.read())
    preview_path = _build_preview(original_path)
    asset = MediaAsset(
        member_id=current_member.id,
        media_type="selfie",
        captured_at=datetime.fromisoformat(captured_at),
        original_path=str(original_path),
        preview_path=str(preview_path),
        is_shared=is_shared,
        note=note,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _serialize_media(asset)


@router.get("/media/selfies", response_model=list[MediaAssetResponse])
def list_selfies(
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> list[MediaAssetResponse]:
    rows = db.scalars(
        select(MediaAsset).where(MediaAsset.member_id == current_member.id).order_by(MediaAsset.captured_at.desc()).limit(30)
    ).all()
    return [_serialize_media(row) for row in rows]


@router.post("/media/selfies/compare", response_model=SelfieCompareResponse)
def compare_selfies(
    payload: SelfieCompareRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> SelfieCompareResponse:
    first_asset = db.scalar(
        select(MediaAsset).where(MediaAsset.member_id == current_member.id, MediaAsset.id == payload.first_asset_id)
    )
    second_asset = db.scalar(
        select(MediaAsset).where(MediaAsset.member_id == current_member.id, MediaAsset.id == payload.second_asset_id)
    )
    if not first_asset or not second_asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对比图片不存在。")

    target_path = _compare_dir(current_member.id) / f"{payload.first_asset_id}-{payload.second_asset_id}.gif"
    _build_compare_gif(Path(first_asset.original_path), Path(second_asset.original_path), target_path)
    gif_url = _media_url(str(target_path))
    if not gif_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="对比动图生成失败。")
    return SelfieCompareResponse(gif_path=str(target_path), gif_url=gif_url)


@router.get("/media/household/selfies", response_model=list[MediaAssetResponse])
def list_household_selfies(
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[MediaAssetResponse]:
    member_ids = db.scalars(select(Member.id).where(Member.household_id == admin.household_id)).all()
    rows = db.scalars(
        select(MediaAsset)
        .where(
            MediaAsset.member_id.in_(member_ids),
            MediaAsset.media_type == "selfie",
            MediaAsset.is_shared.is_(True),
        )
        .order_by(MediaAsset.captured_at.desc())
        .limit(60)
    ).all()
    return [_serialize_media(row) for row in rows]
