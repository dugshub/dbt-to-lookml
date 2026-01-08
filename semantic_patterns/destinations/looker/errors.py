"""Looker-specific exceptions."""

from __future__ import annotations


class LookerAPIError(Exception):
    """Error from Looker or GitHub API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
