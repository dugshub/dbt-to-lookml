"""Command-line interface for semantic-patterns."""

from __future__ import annotations

from pathlib import Path

import click

from semantic_patterns.cli import RichGroup
from semantic_patterns.cli.commands import auth, build, init, validate


@click.group(cls=RichGroup)
@click.version_option()
def cli() -> None:
    """Transform semantic models into BI tool patterns.

    A CLI tool for generating LookML views and explores from semantic models.
    Supports both native semantic-patterns format and dbt Semantic Layer.

    ## Quick Start

    Create a config file:

        $ sp init

    Generate LookML from semantic models:

        $ sp build

    Validate your configuration:

        $ sp validate

    ## Common Workflows

    **Development workflow with dry-run preview:**

        $ sp build --dry-run --verbose

    **Production build and push to Looker:**

        $ sp build --push

    **Build with specific config:**

        $ sp build --config ./configs/production.yml

    **Validate before building:**

        $ sp validate && sp build

    ## Authentication

    Manage credentials for GitHub and Looker:

        $ sp auth status          # Check credential status
        $ sp auth test github     # Test GitHub token
        $ sp auth clear all       # Clear all credentials

    For detailed help on any command:

        $ sp COMMAND --help
    """
    pass


# Register commands
cli.add_command(build)
cli.add_command(init)
cli.add_command(validate)
cli.add_command(auth)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to sp.yml config file",
)
@click.option(
    "--port",
    "-p",
    default=8000,
    help="Port for the API server (default: 8000)",
)
@click.option(
    "--frontend-port",
    default=3000,
    help="Port for the frontend dev server (default: 3000)",
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind to (default: 127.0.0.1)",
)
@click.option(
    "--no-open",
    is_flag=True,
    help="Don't open browser automatically",
)
@click.option(
    "--api-only",
    is_flag=True,
    help="Only run the API server (no frontend)",
)
def serve(
    config: Path | None,
    port: int,
    frontend_port: int,
    host: str,
    no_open: bool,
    api_only: bool,
) -> None:
    """Start the semantic-patterns UI server.

    Launches both the API server and frontend dev server for exploring
    and configuring semantic models through a visual interface.

    Examples:

        # Start both servers (auto-opens browser)
        sp serve

        # Use specific config
        sp serve --config ./sp.yml

        # API server only (no frontend)
        sp serve --api-only
    """
    import atexit
    import os
    import signal
    import subprocess
    import sys
    import time

    # Resolve config path
    config_path: Path | None = None
    if config:
        config_path = config
    else:
        found = find_config()
        if found:
            config_path = found

    if config_path:
        console.print(f"[dim]Config:[/dim] {config_path}")
    else:
        console.print("[yellow]No sp.yml found - starting with empty state[/yellow]")

    console.print()
    console.print("[bold]semantic-patterns[/bold] UI")

    # Track processes for cleanup
    processes: list[subprocess.Popen[bytes]] = []

    def cleanup() -> None:
        """Terminate all spawned processes."""
        for proc in processes:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        time.sleep(0.5)
        for proc in processes:
            try:
                proc.kill()
            except ProcessLookupError:
                pass

    atexit.register(cleanup)

    def signal_handler(signum: int, frame: object) -> None:
        console.print("\n[dim]Shutting down...[/dim]")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Find the client directory
    client_dir = Path(__file__).parent / "app" / "client"
    has_frontend = client_dir.exists() and (client_dir / "package.json").exists()

    # Start backend
    backend_env = os.environ.copy()
    if config_path:
        backend_env["SP_CONFIG_PATH"] = str(config_path.absolute())

    backend_cmd = [
        sys.executable, "-m", "uvicorn",
        "semantic_patterns.app.server.main:create_app",
        "--factory",
        "--host", host,
        "--port", str(port),
        "--log-level", "warning",
    ]

    backend_proc = subprocess.Popen(
        backend_cmd,
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    processes.append(backend_proc)
    console.print(f"[green]API:[/green]      http://{host}:{port}")
    console.print(f"[dim]Docs:[/dim]     http://{host}:{port}/docs")

    # Start frontend (if available and not api-only)
    if has_frontend and not api_only:
        frontend_env = os.environ.copy()
        frontend_env["VITE_API_URL"] = f"http://{host}:{port}"

        frontend_cmd = ["npm", "run", "dev", "--", "--host", "--port", str(frontend_port)]

        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=client_dir,
            env=frontend_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append(frontend_proc)
        console.print(f"[green]Frontend:[/green] http://{host}:{frontend_port}")

        # Open browser to frontend
        if not no_open:
            import threading
            import webbrowser

            def open_browser() -> None:
                time.sleep(2)  # Wait for servers to start
                webbrowser.open(f"http://{host}:{frontend_port}")

            threading.Thread(target=open_browser, daemon=True).start()
    else:
        if not api_only and not has_frontend:
            console.print("[yellow]Frontend not found - run 'npm install' in app/client[/yellow]")

        # Open browser to API docs
        if not no_open:
            import threading
            import webbrowser

            def open_browser() -> None:
                time.sleep(1)
                webbrowser.open(f"http://{host}:{port}/docs")

            threading.Thread(target=open_browser, daemon=True).start()

    console.print()
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    # Wait for processes
    try:
        while True:
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    # Read any output from the failed process
                    name = "API" if i == 0 else "Frontend"
                    console.print(f"\n[red]{name} process stopped unexpectedly[/red]")
                    if proc.stdout:
                        output = proc.stdout.read().decode("utf-8", errors="replace")
                        if output.strip():
                            console.print(f"[dim]{output[-2000:]}[/dim]")  # Last 2000 chars
                    cleanup()
                    sys.exit(1)
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
