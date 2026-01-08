"""Build and validate API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from semantic_patterns.app.server.state import state

router = APIRouter()


class BuildResult(BaseModel):
    """Result of a build operation."""

    success: bool
    message: str
    files: list[str] = []
    stats: dict[str, int] = {}
    errors: list[str] = []


class ValidateResult(BaseModel):
    """Result of a validation operation."""

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


@router.post("/validate")
async def validate() -> ValidateResult:
    """Validate the current configuration and models."""
    errors: list[str] = []
    warnings: list[str] = []

    if state.config is None:
        errors.append("No configuration loaded")
        return ValidateResult(valid=False, errors=errors)

    # Check input path exists
    input_path = state.config.input_path
    if state.config_path and not input_path.is_absolute():
        input_path = state.config_path.parent / input_path

    if not input_path.exists():
        errors.append(f"Input path does not exist: {input_path}")

    # Check models loaded
    if not state.models:
        errors.append("No models loaded")

    # Check explore facts exist
    for explore in state.config.explores:
        fact_name = explore.fact
        if not state.get_model(fact_name):
            errors.append(f"Explore fact model not found: {fact_name}")

    # Warnings for common issues
    for model in state.models:
        if not model.metrics:
            warnings.append(f"Model '{model.name}' has no metrics")
        if not model.primary_entity:
            warnings.append(f"Model '{model.name}' has no primary entity")

    return ValidateResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.post("/build")
async def build(dry_run: bool = False) -> BuildResult:
    """
    Build LookML from the current configuration.

    Note: For production builds, use the CLI command `sp build`.
    This endpoint provides a simplified build for preview purposes.
    """
    if state.config is None or state.config_path is None:
        raise HTTPException(status_code=400, detail="No configuration loaded")

    # For the UI, we recommend using the CLI for actual builds
    # The API is primarily for exploration and validation
    return BuildResult(
        success=True,
        message="Use 'sp build' CLI command for file generation. "
        "API is for exploration and validation.",
        stats=state.get_stats(),
    )


@router.post("/reload")
async def reload() -> dict[str, Any]:
    """Reload models from disk."""
    try:
        state.reload()
        return {
            "success": True,
            "message": "Reloaded successfully",
            "stats": state.get_stats(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
