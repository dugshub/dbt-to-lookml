"""Configuration management for dbt-to-lookml.

Handles saving and loading of last run configuration to enable:
- Prepopulating wizard with previous values
- Quick regeneration with `d2l regenerate` command

Config is stored in ~/.d2l/last_run.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


def get_config_dir() -> Path:
    """Get the configuration directory path.

    Returns:
        Path to ~/.d2l directory.
    """
    return Path.home() / ".d2l"


def get_last_run_path() -> Path:
    """Get the path to the last run configuration file.

    Returns:
        Path to ~/.d2l/last_run.json file.
    """
    return get_config_dir() / "last_run.json"


def load_last_run() -> dict[str, Any] | None:
    """Load the last run configuration from disk.

    Returns:
        Dictionary containing last run parameters, or None if:
        - File doesn't exist
        - File is corrupted/invalid JSON
        - Config version is incompatible

    Example return value:
        {
            "version": "1.0",
            "input_dir": "/path/to/models/semantic_models",
            "output_dir": "/path/to/build/lookml",
            "schema": "analytics",
            "view_prefix": "sm_",
            "explore_prefix": "exp_",
            "connection": "redshift_prod",
            "model_name": "semantic_layer",
            "convert_tz": false,
            "timestamp": "2025-01-18T12:34:56Z"
        }
    """
    config_path = get_last_run_path()

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # Validate config structure
        if not isinstance(config, dict):
            console.print(
                "[yellow]Warning: Invalid config format, ignoring saved config[/yellow]",
                file=None,
                highlight=False,
            )
            return None

        # Check version compatibility
        version = config.get("version", "1.0")
        if version != "1.0":
            console.print(
                f"[yellow]Warning: Config version {version} not supported, "
                f"ignoring saved config[/yellow]",
                file=None,
                highlight=False,
            )
            return None

        return config

    except (json.JSONDecodeError, OSError) as e:
        console.print(
            f"[yellow]Warning: Could not load config: {e}[/yellow]",
            file=None,
            highlight=False,
        )
        return None


def save_last_run(
    input_dir: str | Path,
    output_dir: str | Path,
    schema: str,
    view_prefix: str = "",
    explore_prefix: str = "",
    connection: str = "redshift_test",
    model_name: str = "semantic_model",
    convert_tz: bool | None = None,
) -> None:
    """Save the last run configuration to disk.

    Only saves successful generation runs (not dry-run or validation-only).

    Args:
        input_dir: Input directory containing semantic models
        output_dir: Output directory for LookML files
        schema: Database schema name
        view_prefix: Optional view prefix
        explore_prefix: Optional explore prefix
        connection: Looker connection name
        model_name: Model file name
        convert_tz: Timezone conversion setting (True/False/None)
    """
    config_dir = get_config_dir()

    # Create config directory if it doesn't exist
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        console.print(
            f"[yellow]Warning: Could not create config directory: {e}[/yellow]",
            file=None,
            highlight=False,
        )
        return

    # Build config dictionary
    config = {
        "version": "1.0",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "schema": schema,
        "view_prefix": view_prefix,
        "explore_prefix": explore_prefix,
        "connection": connection,
        "model_name": model_name,
        "convert_tz": convert_tz,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Write to disk
    config_path = get_last_run_path()
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        console.print(
            f"[yellow]Warning: Could not save config: {e}[/yellow]",
            file=None,
            highlight=False,
        )


def clear_config() -> None:
    """Clear all saved configuration.

    Useful for testing or resetting to defaults.
    """
    config_path = get_last_run_path()
    if config_path.exists():
        try:
            config_path.unlink()
        except OSError as e:
            console.print(
                f"[yellow]Warning: Could not clear config: {e}[/yellow]",
                file=None,
                highlight=False,
            )
