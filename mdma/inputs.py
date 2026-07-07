"""Public helpers to inspect and validate a template's @inputs without rendering."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .file_parser import parse_file
from .model import InputDecl
from .schema import validate_inputs as _validate_against_decls


def get_inputs(source: str) -> List[InputDecl]:
    """Parse an .mdma source string and return its ``@inputs`` declarations."""
    return parse_file(source).inputs


def validate_inputs(source: str, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Check an inputs dict against an .mdma source's ``@inputs`` declarations
    without rendering.

    Returns the resolved inputs (declared defaults applied). Raises
    ``MissingInputError`` when a required input is absent and ``MdmaTypeError``
    when a value does not match its declared type.
    """
    return _validate_against_decls(parse_file(source).inputs, inputs or {})
