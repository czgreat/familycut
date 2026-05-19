from collections.abc import Generator
import os
from pathlib import Path
import shutil

import pytest
from sqlalchemy.orm import Session

TEST_RUNTIME_DIR = Path(__file__).resolve().parent / ".pytest-runtime"
TEST_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
os.environ["APP_DATABASE_URL"] = f"sqlite:///{(TEST_RUNTIME_DIR / 'familycut-test.db').resolve()}"
os.environ["APP_MEDIA_ROOT"] = str((TEST_RUNTIME_DIR / "media").resolve())
os.environ["APP_REPORT_IMAGE_ROOT"] = str((TEST_RUNTIME_DIR / "reports").resolve())

from app.core.config import get_settings
from app.db.base import Base
from app.db.runtime_migrations import ensure_runtime_schema
from app.db.session import SessionLocal, engine
from app.services.auth import bootstrap_admin


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    media_root = Path(os.environ["APP_MEDIA_ROOT"])
    report_root = Path(os.environ["APP_REPORT_IMAGE_ROOT"])
    db_file = TEST_RUNTIME_DIR / "familycut-test.db"
    shutil.rmtree(media_root, ignore_errors=True)
    shutil.rmtree(report_root, ignore_errors=True)
    media_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)
    engine.dispose()
    if db_file.exists():
        db_file.unlink()
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)

    settings = get_settings()
    with SessionLocal() as db:
        bootstrap_admin(
            db=db,
            username=settings.bootstrap_admin_username,
            password=settings.bootstrap_admin_password,
            display_name=settings.bootstrap_admin_display_name,
            default_report_generate_hour=settings.default_report_generate_hour,
            default_report_push_hour=settings.default_report_push_hour,
        )

    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
