from datetime import datetime

from sqlalchemy import select

from app.models import DailyReport, Household, Member, NotificationEndpoint
from app.services.reports import push_due_generic_webhooks
from app.workers.jobs import run_due_report_generation


def test_run_due_report_generation_respects_household_schedule(db_session) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None

    household = db_session.get(Household, admin.household_id)
    assert household is not None
    household.report_generate_hour = 9
    household.report_push_hour = 12
    db_session.add(household)
    db_session.commit()

    generated_count = run_due_report_generation(now=datetime(2026, 3, 26, 8, 0, 0))
    db_session.expire_all()
    assert generated_count == 0
    assert db_session.scalars(select(DailyReport)).all() == []

    generated_count = run_due_report_generation(now=datetime(2026, 3, 26, 9, 0, 0))
    db_session.expire_all()
    reports = db_session.scalars(select(DailyReport)).all()

    assert generated_count == 1
    assert len(reports) == 1


def test_daily_push_uses_next_morning_beijing_schedule(db_session, monkeypatch) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None

    household = db_session.get(Household, admin.household_id)
    assert household is not None
    household.report_generate_hour = 23
    household.report_push_hour = 10
    db_session.add(household)
    db_session.add(
        NotificationEndpoint(
            household_id=household.id,
            endpoint_type="generic_webhook",
            name="wechat-gateway",
            target_url="http://push.local/api/push?token=abc",
            enabled=True,
        )
    )
    db_session.commit()

    captured: list[dict] = []

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self) -> dict[str, object]:
            return {"ok": True}

    def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
        captured.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("app.services.reports.httpx.post", fake_post)

    sent_count = push_due_generic_webhooks(db_session, now=datetime(2026, 4, 3, 10, 0, 0))
    assert sent_count == 1
    assert len(captured) == 1
    payload = captured[0]["json"]
    assert captured[0]["url"] == "http://push.local/api/push?token=abc"
    assert payload["type"] == "daily_report"
    assert payload["userId"] == "cz"
    assert payload["title"] == "【cz】2026-04-02 日报"
    assert payload["content"] == "请查收减脂日报长图。"
    assert str(payload["imageUrl"]).startswith("http://localhost:5173/report-files/")
    assert payload["source"] == "jianfei"


def test_weekly_push_runs_monday_1001_beijing(db_session, monkeypatch) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None

    household = db_session.get(Household, admin.household_id)
    assert household is not None
    household.report_push_hour = 10
    db_session.add(household)
    db_session.add(
        NotificationEndpoint(
            household_id=household.id,
            endpoint_type="generic_webhook",
            name="wechat-gateway",
            target_url="http://push.local/api/push?token=abc",
            enabled=True,
        )
    )
    db_session.commit()

    captured: list[dict] = []

    class FakeResponse:
        status_code = 202
        text = "queued"

        def json(self) -> dict[str, object]:
            return {"ok": True, "deferred": True}

    def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
        captured.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("app.services.reports.httpx.post", fake_post)

    sent_count = push_due_generic_webhooks(db_session, now=datetime(2026, 4, 6, 10, 1, 0))
    assert sent_count == 1
    payload = captured[0]["json"]
    assert payload["type"] == "weekly_report"
    assert payload["userId"] == "cz"
    assert payload["title"] == "【cz】2026-04-06 周报"
    assert payload["content"] == "请查收本周周报长图。"
    assert payload["periodStart"] == "2026-03-30"
    assert payload["periodEnd"] == "2026-04-05"
    assert str(payload["imageUrl"]).startswith("http://localhost:5173/report-files/")


def test_monthly_push_runs_first_day_1002_beijing(db_session, monkeypatch) -> None:
    admin = db_session.scalar(select(Member).where(Member.username == "admin"))
    assert admin is not None

    household = db_session.get(Household, admin.household_id)
    assert household is not None
    household.report_push_hour = 10
    db_session.add(household)
    db_session.add(
        NotificationEndpoint(
            household_id=household.id,
            endpoint_type="generic_webhook",
            name="wechat-gateway",
            target_url="http://push.local/api/push?token=abc",
            enabled=True,
        )
    )
    db_session.commit()

    captured: list[dict] = []

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self) -> dict[str, object]:
            return {"ok": True}

    def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
        captured.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("app.services.reports.httpx.post", fake_post)

    sent_count = push_due_generic_webhooks(db_session, now=datetime(2026, 4, 1, 10, 2, 0))
    assert sent_count == 1
    payload = captured[0]["json"]
    assert payload["type"] == "monthly_report"
    assert payload["userId"] == "cz"
    assert payload["title"] == "【cz】2026-03 月报"
    assert payload["content"] == "请查收本月月报长图。"
    assert payload["periodStart"] == "2026-03-01"
    assert payload["periodEnd"] == "2026-03-31"
    assert str(payload["imageUrl"]).startswith("http://localhost:5173/report-files/")
