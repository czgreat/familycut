import logging

from app.core.config import get_settings
from app.db.base import Base
from app.db.runtime_migrations import audit_member_username_state, ensure_runtime_schema, validate_member_username_integrity
from app.db.session import SessionLocal, engine
from app.services.auth import bootstrap_admin


logger = logging.getLogger(__name__)


def initialize_runtime() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
    settings = get_settings()
    username_audit = audit_member_username_state(engine)
    duplicate_usernames = username_audit["duplicate_usernames"]
    if duplicate_usernames:
        preview = ", ".join(
            f"{item['username']} x{item['member_count']}"
            for item in duplicate_usernames[:5]
        )
        logger.warning("Detected duplicate member usernames in database: %s", preview)
    if settings.enforce_global_unique_username:
        validate_member_username_integrity(engine, require_global_unique_username=True)
    with SessionLocal() as db:
        bootstrap_admin(
            db=db,
            username=settings.bootstrap_admin_username,
            password=settings.bootstrap_admin_password,
            display_name=settings.bootstrap_admin_display_name,
            default_report_generate_hour=settings.default_report_generate_hour,
            default_report_push_hour=settings.default_report_push_hour,
        )


def main() -> None:
    initialize_runtime()


if __name__ == "__main__":
    main()
