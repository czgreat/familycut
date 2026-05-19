from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_member, require_admin
from app.db.session import get_db
from app.models import DailyReport, MealEntry, MeasurementRecord, MediaAsset, Member
from app.schemas.report import DailyReportResponse, DashboardResponse, PeriodicReportResponse
from app.services.reports import generate_daily_report, generate_periodic_report, report_image_url


router = APIRouter(prefix="/reports", tags=["reports"])


def _serialize_report(report: DailyReport) -> DailyReportResponse:
    return DailyReportResponse(
        id=report.id,
        report_date=report.report_date,
        status=report.status,
        payload=report.payload,
        image_path=report.image_path,
        image_url=report_image_url(report),
        is_shared=report.is_shared,
    )


def _serialize_periodic_report(payload: dict) -> PeriodicReportResponse:
    return PeriodicReportResponse(
        report_type=payload["report_type"],
        period_start=payload["period_start"],
        period_end=payload["period_end"],
        status=payload["status"],
        payload=payload["payload"],
        image_path=payload["image_path"],
        image_url=payload["image_url"],
    )


@router.get("/daily/{report_date}", response_model=DailyReportResponse)
def get_or_generate_daily_report(
    report_date: date,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> DailyReportResponse:
    report = generate_daily_report(db, current_member, report_date)
    return _serialize_report(report)


@router.get("/weekly/{start_date}", response_model=PeriodicReportResponse)
def get_weekly_report(
    start_date: date,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> PeriodicReportResponse:
    period_end = start_date + timedelta(days=6)
    payload = generate_periodic_report(db, current_member, "weekly", start_date, period_end)
    return _serialize_periodic_report(payload)


@router.get("/monthly/{year_month}", response_model=PeriodicReportResponse)
def get_monthly_report(
    year_month: str,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> PeriodicReportResponse:
    period_start = datetime.strptime(year_month, "%Y-%m").date().replace(day=1)
    next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    period_end = next_month - timedelta(days=1)
    payload = generate_periodic_report(db, current_member, "monthly", period_start, period_end)
    return _serialize_periodic_report(payload)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard_summary(admin: Member = Depends(require_admin), db: Session = Depends(get_db)) -> DashboardResponse:
    household_member_ids = db.scalars(select(Member.id).where(Member.household_id == admin.household_id)).all()
    return DashboardResponse(
        member_count=len(household_member_ids),
        measurement_count=db.scalar(select(func.count(MeasurementRecord.id)).where(MeasurementRecord.member_id.in_(household_member_ids))) or 0,
        meal_count=db.scalar(select(func.count(MealEntry.id)).where(MealEntry.member_id.in_(household_member_ids))) or 0,
        shared_media_count=db.scalar(
            select(func.count(MediaAsset.id)).where(MediaAsset.member_id.in_(household_member_ids), MediaAsset.is_shared.is_(True))
        )
        or 0,
    )


@router.get("/history", response_model=list[DailyReportResponse])
def household_reports(admin: Member = Depends(require_admin), db: Session = Depends(get_db)) -> list[DailyReportResponse]:
    household_member_ids = db.scalars(select(Member.id).where(Member.household_id == admin.household_id)).all()
    rows = db.scalars(select(DailyReport).where(DailyReport.member_id.in_(household_member_ids)).order_by(DailyReport.report_date.desc())).all()
    return [_serialize_report(row) for row in rows]


@router.get("/recent", response_model=list[DailyReportResponse])
def my_recent_reports(
    limit: int = 7,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> list[DailyReportResponse]:
    safe_limit = min(max(limit, 1), 31)
    rows = db.scalars(
        select(DailyReport)
        .where(DailyReport.member_id == current_member.id)
        .order_by(DailyReport.report_date.desc())
        .limit(safe_limit)
    ).all()
    return [_serialize_report(row) for row in rows]
