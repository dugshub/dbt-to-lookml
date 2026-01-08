"""Models API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException

from semantic_patterns.app.server.state import state
from semantic_patterns.domain import Dimension, Entity, Measure, Metric, ProcessedModel

router = APIRouter()


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """Get summary statistics for the loaded models."""
    return state.get_stats()


@router.get("/models")
async def list_models() -> list[dict[str, Any]]:
    """List all models with summary info."""
    return [
        {
            "name": m.name,
            "label": m.label,
            "description": m.description,
            "dimensions": len(m.dimensions),
            "measures": len(m.measures),
            "metrics": len(m.metrics),
            "metric_variants": m.total_variant_count,
            "entities": len(m.entities),
            "primary_entity": m.primary_entity.name if m.primary_entity else None,
            "entity_group": m.entity_group,
            "time_dimension": m.time_dimension,
        }
        for m in state.models
    ]


@router.get("/models/{name}")
async def get_model(name: str) -> ProcessedModel:
    """Get a single model with all details."""
    model = state.get_model(name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return model


@router.get("/models/{name}/dimensions")
async def get_model_dimensions(name: str) -> list[Dimension]:
    """Get dimensions for a model."""
    model = state.get_model(name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return model.dimensions


@router.get("/models/{name}/measures")
async def get_model_measures(name: str) -> list[Measure]:
    """Get measures for a model."""
    model = state.get_model(name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return model.measures


@router.get("/models/{name}/metrics")
async def get_model_metrics(name: str) -> list[Metric]:
    """Get metrics for a model."""
    model = state.get_model(name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return model.metrics


@router.get("/models/{name}/entities")
async def get_model_entities(name: str) -> list[Entity]:
    """Get entities for a model."""
    model = state.get_model(name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return model.entities


@router.get("/dimensions")
async def list_all_dimensions() -> list[dict[str, Any]]:
    """List all dimensions across all models."""
    result = []
    for model in state.models:
        for dim in model.dimensions:
            result.append({
                "model": model.name,
                "entity": model.entity_group,
                **dim.model_dump(),
            })
    return result


@router.get("/measures")
async def list_all_measures() -> list[dict[str, Any]]:
    """List all measures across all models."""
    result = []
    for model in state.models:
        for measure in model.measures:
            result.append({
                "model": model.name,
                "entity": model.entity_group,
                **measure.model_dump(),
            })
    return result


@router.get("/metrics")
async def list_all_metrics() -> list[dict[str, Any]]:
    """List all metrics across all models."""
    result = []
    for model in state.models:
        for metric in model.metrics:
            result.append({
                "model": model.name,
                "entity": model.entity_group,
                **metric.model_dump(),
            })
    return result


@router.get("/entities")
async def list_all_entities() -> list[dict[str, Any]]:
    """List all entities across all models."""
    result = []
    for model in state.models:
        for entity in model.entities:
            result.append({
                "model": model.name,
                **entity.model_dump(),
            })
    return result
