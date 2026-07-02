"""Small shared helpers used by the evaluator, filters, and schema modules."""

from __future__ import annotations

from typing import Any

from .errors import MdmaTypeError


def typename(value: Any) -> str:
    """Map a Python runtime value to the type name used in mdma error messages."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def truthy(value: Any) -> bool:
    """Falsy values: None, False, 0, 0.0, "", [], {}. Everything else is truthy."""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return bool(value)


def format_number(value: float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def to_display_string(value: Any) -> str:
    """Render a value for direct output inside a {{ }} interpolation."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return format_number(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(to_display_string(v) for v in value)
    if isinstance(value, dict):
        raise MdmaTypeError("string", "object")
    return str(value)
