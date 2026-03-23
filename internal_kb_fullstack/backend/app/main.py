from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.api.routes import admin, auth, connectors, documents, glossary, health, search
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.engine import dispose_engine, get_engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    get_engine()
    yield
    await dispose_engine()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(connectors.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(glossary.router)
app.include_router(admin.router)
