"""AST node types for block bodies (text/control-flow) and expressions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple, Union

# --- Expression AST -----------------------------------------------------


@dataclass
class Literal:
    value: Any


@dataclass
class ArrayLiteral:
    items: List["Expr"]


@dataclass
class Var:
    path: List[str]


@dataclass
class Not:
    operand: "Expr"


@dataclass
class BinOp:
    op: str  # 'and' | 'or' | '==' | '!=' | '>' | '>=' | '<' | '<='
    left: "Expr"
    right: "Expr"


@dataclass
class FilterCall:
    target: "Expr"
    name: str
    args: List["Expr"] = field(default_factory=list)


Expr = Union[Literal, ArrayLiteral, Var, Not, BinOp, FilterCall]

# --- Block-body AST -------------------------------------------------------


@dataclass
class TextNode:
    text: str


@dataclass
class ExprNode:
    expr: Expr


@dataclass
class IfNode:
    # Each branch is (condition, body). The `else` branch has condition=None.
    branches: List[Tuple[Optional[Expr], List["Node"]]]


@dataclass
class ForNode:
    var_name: str
    iterable: Expr
    body: List["Node"]


Node = Union[TextNode, ExprNode, IfNode, ForNode]
