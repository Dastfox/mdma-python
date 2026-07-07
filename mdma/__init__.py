"""mdma — a typed Markdown templating format.

See https://github.com/ (project README) for the full language specification.
"""

from .errors import (
    DuplicateNameError,
    FilterError,
    MdmaError,
    MdmaReferenceError,
    MdmaSyntaxError,
    MdmaTypeError,
    MissingInputError,
)
from .file_parser import parse_file
from .inputs import get_inputs, validate_inputs
from .model import ParsedTemplate
from .output import write_output
from .renderer import render, render_file, render_template

__version__ = "0.3.0"

__all__ = [
    "render",
    "render_file",
    "render_template",
    "parse_file",
    "ParsedTemplate",
    "get_inputs",
    "validate_inputs",
    "write_output",
    "MdmaError",
    "MdmaSyntaxError",
    "MissingInputError",
    "MdmaTypeError",
    "MdmaReferenceError",
    "FilterError",
    "DuplicateNameError",
    "__version__",
]
