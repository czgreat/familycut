from datetime import datetime

from pydantic import BaseModel


class MediaAssetResponse(BaseModel):
    id: str
    media_type: str
    captured_at: datetime
    original_path: str
    preview_path: str | None
    original_url: str | None = None
    preview_url: str | None = None
    is_shared: bool
    note: str | None


class SelfieCompareRequest(BaseModel):
    first_asset_id: str
    second_asset_id: str


class SelfieCompareResponse(BaseModel):
    gif_path: str
    gif_url: str
