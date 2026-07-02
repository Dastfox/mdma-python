"""Validates and applies defaults to a raw inputs dict against @inputs declarations."""

from __future__ import annotations

from typing import Any, Dict, List

from .errors import MdmaTypeError, MissingInputError
from .model import InputDecl
from .util import typename

_SCALAR_CHECKERS = {
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
}


def validate_inputs(decls: List[InputDecl], raw_inputs: Dict[str, Any]) -> Dict[str, Any]:
    raw_inputs = raw_inputs or {}
    result: Dict[str, Any] = {}
    for decl in decls:
        if decl.name in raw_inputs:
            value = raw_inputs[decl.name]
        elif decl.has_default:
            value = decl.default
        else:
            raise MissingInputError(decl.name)
        _check_type(decl.type, value)
        result[decl.name] = value
    return result


def _check_type(type_: str, value: Any) -> None:
    if type_.endswith("[]"):
        scalar = type_[:-2]
        if not isinstance(value, list):
            raise MdmaTypeError(type_, typename(value))
        checker = _SCALAR_CHECKERS[scalar]
        for item in value:
            if not checker(item):
                raise MdmaTypeError(type_, f"{scalar}[] containing {typename(item)}")
        return
    if not _SCALAR_CHECKERS[type_](value):
        raise MdmaTypeError(type_, typename(value))
