"""Config API routes."""

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from semantic_patterns.app.server.state import state
from semantic_patterns.config import SPConfig

router = APIRouter()


class ConfigResponse(BaseModel):
    """Response containing the current config."""

    path: str
    config: dict[str, Any]


class ConfigUpdateRequest(BaseModel):
    """Request to update config."""

    config: dict[str, Any]


@router.get("/config")
async def get_config() -> ConfigResponse:
    """Get the current sp.yml configuration."""
    if state.config is None:
        raise HTTPException(status_code=404, detail="No config loaded")

    return ConfigResponse(
        path=str(state.config_path) if state.config_path else "",
        config=state.config.model_dump(by_alias=True),
    )


@router.put("/config")
async def update_config(request: ConfigUpdateRequest) -> ConfigResponse:
    """Update the sp.yml configuration."""
    if state.config_path is None:
        raise HTTPException(status_code=404, detail="No config file path")

    try:
        # Validate the new config
        new_config = SPConfig.model_validate(request.config)

        # Write to file
        yaml_content = yaml.dump(
            request.config,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        state.config_path.write_text(yaml_content, encoding="utf-8")

        # Reload state
        state.reload()

        return ConfigResponse(
            path=str(state.config_path),
            config=state.config.model_dump(by_alias=True) if state.config else {},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/config/raw")
async def get_config_raw() -> dict[str, str]:
    """Get the raw YAML content of sp.yml."""
    if state.config_path is None:
        raise HTTPException(status_code=404, detail="No config file path")

    content = state.config_path.read_text(encoding="utf-8")
    return {"content": content, "path": str(state.config_path)}


@router.put("/config/raw")
async def update_config_raw(request: dict[str, str]) -> dict[str, str]:
    """Update sp.yml with raw YAML content."""
    if state.config_path is None:
        raise HTTPException(status_code=404, detail="No config file path")

    content = request.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="No content provided")

    try:
        # Validate by parsing
        SPConfig.from_yaml(content)

        # Write to file
        state.config_path.write_text(content, encoding="utf-8")

        # Reload state
        state.reload()

        return {"content": content, "path": str(state.config_path)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
