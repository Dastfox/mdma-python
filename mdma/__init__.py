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
from .output import write_output
from .renderer import render, render_file

__version__ = "0.1.0"

__all__ = [
    "render",
    "render_file",
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
