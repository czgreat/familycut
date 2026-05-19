from datetime import date

from pydantic import BaseModel


class DailyReportResponse(BaseModel):
    id: str
    report_date: date
    status: str
    payload: dict
    image_path: str | None
    image_url: str | None = None
    is_shared: bool


class DashboardResponse(BaseModel):
    member_count: int
    measurement_count: int
    meal_count: int
    shared_media_count: int


class PeriodicReportResponse(BaseModel):
    report_type: str
    period_start: date
    period_end: date
    status: str
    payload: dict
    image_path: str | None
    image_url: str | None = None
