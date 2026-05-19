from sqlalchemy import create_engine, text
import pytest

from app.db.runtime_migrations import audit_member_username_state, ensure_runtime_schema, validate_member_username_integrity


def _legacy_members_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE members (
                    id TEXT PRIMARY KEY,
                    household_id TEXT NOT NULL,
                    username VARCHAR(64) NOT NULL
                )
                """
            )
        )
    return engine


def test_audit_member_username_state_reports_legacy_duplicates() -> None:
    engine = _legacy_members_engine()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO members (id, household_id, username) VALUES (:id, :household_id, :username)"),
            [
                {"id": "1", "household_id": "h1", "username": "admin"},
                {"id": "2", "household_id": "h2", "username": "admin"},
            ],
        )

    audit = audit_member_username_state(engine)

    assert audit["duplicate_usernames"] == [{"username": "admin", "member_count": 2}]
    assert audit["has_global_unique_username_constraint"] is False
    assert audit["has_household_scoped_unique_username_constraint"] is False


def test_audit_member_username_state_detects_global_unique_index() -> None:
    engine = _legacy_members_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE UNIQUE INDEX uq_member_username ON members (username)"))
        connection.execute(
            text("INSERT INTO members (id, household_id, username) VALUES (:id, :household_id, :username)"),
            {"id": "1", "household_id": "h1", "username": "admin"},
        )

    audit = audit_member_username_state(engine)

    assert audit["duplicate_usernames"] == []
    assert audit["has_global_unique_username_constraint"] is True


def test_validate_member_username_integrity_rejects_duplicates() -> None:
    engine = _legacy_members_engine()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO members (id, household_id, username) VALUES (:id, :household_id, :username)"),
            [
                {"id": "1", "household_id": "h1", "username": "admin"},
                {"id": "2", "household_id": "h2", "username": "admin"},
            ],
        )

    with pytest.raises(RuntimeError, match="Detected duplicate member usernames"):
        validate_member_username_integrity(engine)


def test_validate_member_username_integrity_requires_global_unique_constraint() -> None:
    engine = _legacy_members_engine()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO members (id, household_id, username) VALUES (:id, :household_id, :username)"),
            {"id": "1", "household_id": "h1", "username": "admin"},
        )

    with pytest.raises(RuntimeError, match="APP_ENFORCE_GLOBAL_UNIQUE_USERNAME=1"):
        validate_member_username_integrity(engine, require_global_unique_username=True)


def test_ensure_runtime_schema_adds_global_unique_index_when_safe() -> None:
    engine = _legacy_members_engine()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO members (id, household_id, username) VALUES (:id, :household_id, :username)"),
            [
                {"id": "1", "household_id": "h1", "username": "admin"},
                {"id": "2", "household_id": "h2", "username": "wdc"},
            ],
        )

    ensure_runtime_schema(engine)
    audit = audit_member_username_state(engine)

    assert audit["has_global_unique_username_constraint"] is True


def test_ensure_runtime_schema_skips_global_unique_index_when_duplicates_exist() -> None:
    engine = _legacy_members_engine()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO members (id, household_id, username) VALUES (:id, :household_id, :username)"),
            [
                {"id": "1", "household_id": "h1", "username": "admin"},
                {"id": "2", "household_id": "h2", "username": "admin"},
            ],
        )

    ensure_runtime_schema(engine)
    audit = audit_member_username_state(engine)

    assert audit["has_global_unique_username_constraint"] is False
