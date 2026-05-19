from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.core.security import get_password_hash
from app.models import Household, Invitation, Member


def test_register_by_invite_rejects_duplicate_username_globally(db_session) -> None:
    household = Household(name="第二家庭")
    db_session.add(household)
    db_session.flush()

    invitation = Invitation(household_id=household.id, code="SECOND1234", role="member")
    db_session.add(invitation)
    db_session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register-by-invite",
            json={
                "code": invitation.code,
                "username": "admin",
                "password": "1099040334",
                "display_name": "重复账号测试",
                "sex": "male",
                "birth_year": 1990,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "当前系统中已存在同名用户"


def test_database_rejects_duplicate_username_globally(db_session) -> None:
    household = Household(name="第二家庭")
    db_session.add(household)
    db_session.flush()

    second_member = Member(
        household_id=household.id,
        username="admin",
        password_hash=get_password_hash("another-password-123"),
        display_name="第二家庭管理员",
        role="member",
    )
    db_session.add(second_member)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_update_me_rejects_changing_sex_and_birth_year_after_first_set(db_session) -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "1099040334"},
        )
        assert login.status_code == 200
        token = login.json()["tokens"]["access_token"]

        initial = client.put(
            "/api/v1/members/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"sex": "male", "birth_year": 1990, "height_cm": 175},
        )
        assert initial.status_code == 200

        changed = client.put(
            "/api/v1/members/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"sex": "female", "birth_year": 1992},
        )

    assert changed.status_code == 400
    assert changed.json()["detail"] in {"性别首次设置后不可修改", "出生年份首次设置后不可修改"}
