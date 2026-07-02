"""Exception types for the mdma template engine.

Message text follows the error table in spec.md section 7.1 exactly, so
``str(exc)`` is stable and suitable for display to end users.
"""

from __future__ import annotations


class MdmaError(Exception):
    """Base class for all errors raised while parsing or rendering an .mdma file."""


class MdmaSyntaxError(MdmaError):
    """The .mdma source does not conform to the grammar."""


class MissingInputError(MdmaError):
    """A required input (no default) was not supplied at render time."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"MissingInput: {name}")


class MdmaTypeError(MdmaError):
    """An input value's runtime type does not match its declared type."""

    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"TypeError: expected {expected}, got {actual}")


class MdmaReferenceError(MdmaError):
    """A block or variable reference could not be resolved."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @classmethod
    def forward_block(cls, name: str) -> "MdmaReferenceError":
        return cls(f"ReferenceError: block '{name}' not yet rendered")

    @classmethod
    def undefined(cls, name: str) -> "MdmaReferenceError":
        return cls(f"ReferenceError: '{name}' is not defined")


class FilterError(MdmaError):
    """A filter was applied to a value of the wrong type."""

    def __init__(self, filter_name: str, expected_type: str) -> None:
        self.filter_name = filter_name
        self.expected_type = expected_type
        super().__init__(f"FilterError: '{filter_name}' expects {expected_type}")


class DuplicateNameError(MdmaError):
    """Two items in a `<multiple:>` block computed the same `<name:>` value."""

    def __init__(self, computed_name: str, block_name: str) -> None:
        self.computed_name = computed_name
        self.block_name = block_name
        super().__init__(f"DuplicateName: '{computed_name}' in block '{block_name}'")
