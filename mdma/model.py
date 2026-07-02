"""Data model for a parsed .mdma file: inputs declarations and blocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class InputDecl:
    name: str
    type: str  # one of: string, string[], number, number[], boolean, object, object[]
    has_default: bool
    default: Any = None


@dataclass
class Block:
    name: str
    multiple_var: Optional[str]
    multiple_source: Optional[str]
    name_expr: Optional[Any]  # Expr, see template_ast.py; only set alongside multiple_var
    body: List[Any]  # template AST nodes, see template_ast.py


@dataclass
class ParsedTemplate:
    inputs: List[InputDecl]
    blocks: List[Block]
