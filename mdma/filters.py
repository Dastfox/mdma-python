"""Built-in filters, per spec.md section 6 and docs/filters.md."""

from __future__ import annotations

from typing import Any, List

from .errors import FilterError, MdmaSyntaxError
from .util import to_display_string, truthy


def _is_str(v: Any) -> bool:
    return isinstance(v, str)


def _is_list(v: Any) -> bool:
    return isinstance(v, list)


def f_length(value: Any, args: List[Any]) -> int:
    if _is_str(value) or _is_list(value):
        return len(value)
    raise FilterError("length", "string or array")


def f_lower(value: Any, args: List[Any]) -> str:
    if not _is_str(value):
        raise FilterError("lower", "string")
    return value.lower()


def f_upper(value: Any, args: List[Any]) -> str:
    if not _is_str(value):
        raise FilterError("upper", "string")
    return value.upper()


def f_trim(value: Any, args: List[Any]) -> str:
    if not _is_str(value):
        raise FilterError("trim", "string")
    return value.strip()


def f_join(value: Any, args: List[Any]) -> str:
    if not _is_list(value):
        raise FilterError("join", "array")
    sep = args[0] if args else ""
    return sep.join(to_display_string(v) for v in value)


def f_first(value: Any, args: List[Any]) -> Any:
    if not _is_list(value):
        raise FilterError("first", "array")
    return value[0] if value else None


def f_last(value: Any, args: List[Any]) -> Any:
    if not _is_list(value):
        raise FilterError("last", "array")
    return value[-1] if value else None


def f_default(value: Any, args: List[Any]) -> Any:
    fallback = args[0] if args else None
    return value if truthy(value) else fallback


def f_reverse(value: Any, args: List[Any]) -> Any:
    if _is_str(value):
        return value[::-1]
    if _is_list(value):
        return list(reversed(value))
    raise FilterError("reverse", "array or string")


def f_sort(value: Any, args: List[Any]) -> Any:
    if not _is_list(value):
        raise FilterError("sort", "array")
    return sorted(value)


def f_unique(value: Any, args: List[Any]) -> Any:
    if not _is_list(value):
        raise FilterError("unique", "array")
    seen: List[Any] = []
    for v in value:
        if v not in seen:
            seen.append(v)
    return seen


FILTERS = {
    "length": f_length,
    "lower": f_lower,
    "upper": f_upper,
    "trim": f_trim,
    "join": f_join,
    "first": f_first,
    "last": f_last,
    "default": f_default,
    "reverse": f_reverse,
    "sort": f_sort,
    "unique": f_unique,
}


def apply_filter(name: str, value: Any, args: List[Any]) -> Any:
    fn = FILTERS.get(name)
    if fn is None:
        raise MdmaSyntaxError(f"Unknown filter: '{name}'")
    return fn(value, args)
