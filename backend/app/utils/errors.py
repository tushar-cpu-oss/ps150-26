"""Application error type. Rendered as {"success": false, "error": {...}}."""
from typing import Any


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def not_found(code: str, message: str) -> AppError:
    return AppError(404, code, message)
