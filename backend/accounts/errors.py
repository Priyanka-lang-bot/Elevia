from __future__ import annotations

from typing import Optional


class AccountError(Exception):
    """A user-facing error. `field` lets the UI show it under the right input."""

    def __init__(self, message: str, status_code: int = 400, field: Optional[str] = None,
                 code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.field = field
        self.code = code
