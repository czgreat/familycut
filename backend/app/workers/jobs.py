from __future__ import annotations

from datetime import datetime
from time import sleep

from sqlalchemy import select

from app.db.init_runtime import initialize_runtime
from app.db.session import SessionLocal
from app.models import Household, Member
from app.services.reports import _as_beijing_datetime, generate_daily_report, push_due_generic_webhooks


def run_due_report_generation(now: datetime | None = None) -> int:
    current_time = _as_beijing_datetime(now)
    report_date = current_time.date()
    generated_count = 0
    with SessionLocal() as db:
        household_ids = []
        if current_time.minute == 0:
            household_ids = db.scalars(
                select(Household.id).where(Household.report_generate_hour == current_time.hour)
            ).all()
        if household_ids:
            members = db.scalars(
                select(Member)
                .where(Member.household_id.in_(household_ids), Member.is_active.is_(True))
                .order_by(Member.created_at.asc())
            ).all()
            for member in members:
                generate_daily_report(db, member, report_date)
                generated_count += 1

        push_due_generic_webhooks(db, now=current_time)
    return generated_count


def main() -> None:
    initialize_runtime()
    while True:
        run_due_report_generation()
        sleep(60)


if __name__ == "__main__":
    main()
