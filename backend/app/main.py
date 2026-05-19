from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.db.init_runtime import initialize_runtime


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_runtime()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.mount("/media-files", StaticFiles(directory=settings.media_root), name="media-files")
app.mount("/report-files", StaticFiles(directory=settings.report_image_root), name="report-files")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
