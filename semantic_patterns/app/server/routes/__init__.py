"""API route modules."""

from semantic_patterns.app.server.routes.config import router as config_router
from semantic_patterns.app.server.routes.models import router as models_router
from semantic_patterns.app.server.routes.build import router as build_router

__all__ = ["config_router", "models_router", "build_router"]
