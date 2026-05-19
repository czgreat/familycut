from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _column_names(engine: Engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _ensure_columns(engine: Engine, table_name: str, column_definitions: Iterable[tuple[str, str]]) -> None:
    existing_columns = _column_names(engine, table_name)
    if not existing_columns:
        return

    with engine.begin() as connection:
        for column_name, ddl in column_definitions:
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))


def _unique_column_sets(engine: Engine, table_name: str) -> list[list[str]]:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return []

    unique_sets: list[list[str]] = []
    for constraint in inspector.get_unique_constraints(table_name):
        column_names = list(constraint.get("column_names") or [])
        if column_names:
            unique_sets.append(column_names)

    for index in inspector.get_indexes(table_name):
        if not index.get("unique"):
            continue
        column_names = list(index.get("column_names") or [])
        if column_names:
            unique_sets.append(column_names)

    return unique_sets


def _ensure_unique_index(engine: Engine, table_name: str, index_name: str, column_names: tuple[str, ...]) -> None:
    existing_unique_sets = _unique_column_sets(engine, table_name)
    if list(column_names) in existing_unique_sets:
        return

    columns_sql = ", ".join(column_names)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_sql})"))


def audit_member_username_state(engine: Engine) -> dict[str, object]:
    inspector = inspect(engine)
    if "members" not in inspector.get_table_names():
        return {
            "table_exists": False,
            "duplicate_usernames": [],
            "has_global_unique_username_constraint": False,
            "has_household_scoped_unique_username_constraint": False,
        }

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT username, COUNT(*) AS member_count
                FROM members
                GROUP BY username
                HAVING COUNT(*) > 1
                ORDER BY username
                """
            )
        ).mappings()
        duplicate_usernames = [
            {
                "username": str(row["username"]),
                "member_count": int(row["member_count"]),
            }
            for row in rows
        ]

    unique_sets = _unique_column_sets(engine, "members")
    return {
        "table_exists": True,
        "duplicate_usernames": duplicate_usernames,
        "has_global_unique_username_constraint": ["username"] in unique_sets,
        "has_household_scoped_unique_username_constraint": ["household_id", "username"] in unique_sets,
    }


def validate_member_username_integrity(
    engine: Engine,
    *,
    require_global_unique_username: bool = False,
) -> dict[str, object]:
    audit = audit_member_username_state(engine)
    duplicates = audit["duplicate_usernames"]
    if duplicates:
        preview = ", ".join(
            f"{item['username']} x{item['member_count']}"
            for item in duplicates[:5]
        )
        raise RuntimeError(
            "Detected duplicate member usernames in the database. "
            "Run scripts/audit_member_usernames.py and complete the username cleanup before rollout. "
            f"Examples: {preview}"
        )

    if require_global_unique_username and not audit["has_global_unique_username_constraint"]:
        raise RuntimeError(
            "APP_ENFORCE_GLOBAL_UNIQUE_USERNAME=1 but members.username is not protected by a global "
            "unique constraint or unique index. Apply the manual username rollout SQL first."
        )

    return audit


def ensure_runtime_schema(engine: Engine) -> None:
    _ensure_columns(
        engine,
        "ai_provider_settings",
        (
            ("proxy_enabled", "proxy_enabled BOOLEAN NOT NULL DEFAULT 0"),
            ("proxy_url", "proxy_url VARCHAR(255)"),
        ),
    )
    _ensure_columns(
        engine,
        "nutrition_drafts",
        (
            ("draft_type", "draft_type VARCHAR(24) NOT NULL DEFAULT 'label'"),
            ("food_name", "food_name VARCHAR(120)"),
            ("hint_text", "hint_text VARCHAR(255)"),
            ("status", "status VARCHAR(24) NOT NULL DEFAULT 'processing'"),
            ("estimated_grams", "estimated_grams FLOAT"),
            ("error_message", "error_message VARCHAR(255)"),
            ("completed_at", "completed_at TIMESTAMP"),
        ),
    )

    username_audit = audit_member_username_state(engine)
    if (
        username_audit["table_exists"]
        and not username_audit["duplicate_usernames"]
        and not username_audit["has_global_unique_username_constraint"]
    ):
        _ensure_unique_index(engine, "members", "uq_members_username", ("username",))
