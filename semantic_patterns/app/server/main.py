"""FastAPI application for semantic-patterns UI."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from semantic_patterns.app.server.routes import (
    build_router,
    config_router,
    models_router,
)
from semantic_patterns.app.server.state import state


def create_app(config_path: Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    # Check environment variable for config path
    if config_path is None:
        env_path = os.environ.get("SP_CONFIG_PATH")
        if env_path:
            config_path = Path(env_path)
    app = FastAPI(
        title="Semantic Patterns",
        description="Visual interface for semantic model exploration and configuration",
        version="0.3.0",
    )

    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load state on startup
    @app.on_event("startup")
    async def startup_event() -> None:
        state.load(config_path)

    # Mount API routes
    app.include_router(config_router, prefix="/api", tags=["config"])
    app.include_router(models_router, prefix="/api", tags=["models"])
    app.include_router(build_router, prefix="/api", tags=["build"])

    # Health check
    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def create_app_with_static(
    config_path: Path | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    """Create app with static file serving for production."""
    app = create_app(config_path)

    if static_dir and static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
