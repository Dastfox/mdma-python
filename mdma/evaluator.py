"""Scope model and expression evaluator."""

from __future__ import annotations

import operator
from typing import Any, Dict, List, Set

from .errors import MdmaReferenceError
from .filters import apply_filter
from .template_ast import ArrayLiteral, BinOp, Expr, FilterCall, Literal, Not, Var
from .util import truthy

_COMPARATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


class Scope:
    """Variable resolution: innermost loop bindings, then rendered blocks, then inputs."""

    def __init__(
        self,
        blocks: Dict[str, Any],
        inputs: Dict[str, Any],
        all_block_names: Set[str],
        layers: List[Dict[str, Any]] = None,
    ) -> None:
        self.blocks = blocks
        self.inputs = inputs
        self.all_block_names = all_block_names
        self.layers = layers or []

    def child(self, bindings: Dict[str, Any]) -> "Scope":
        return Scope(self.blocks, self.inputs, self.all_block_names, self.layers + [bindings])

    def resolve_root(self, name: str) -> Any:
        for layer in reversed(self.layers):
            if name in layer:
                return layer[name]
        if name in self.blocks:
            return self.blocks[name]
        if name in self.all_block_names:
            raise MdmaReferenceError.forward_block(name)
        if name in self.inputs:
            return self.inputs[name]
        raise MdmaReferenceError.undefined(name)


def resolve_var(path: List[str], scope: Scope) -> Any:
    value = scope.resolve_root(path[0])
    for key in path[1:]:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            raise MdmaReferenceError.undefined(".".join(path))
    return value


def evaluate(expr: Expr, scope: Scope) -> Any:
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, ArrayLiteral):
        return [evaluate(item, scope) for item in expr.items]
    if isinstance(expr, Var):
        return resolve_var(expr.path, scope)
    if isinstance(expr, Not):
        return not truthy(evaluate(expr.operand, scope))
    if isinstance(expr, BinOp):
        if expr.op == "and":
            left = evaluate(expr.left, scope)
            return evaluate(expr.right, scope) if truthy(left) else left
        if expr.op == "or":
            left = evaluate(expr.left, scope)
            return left if truthy(left) else evaluate(expr.right, scope)
        left = evaluate(expr.left, scope)
        right = evaluate(expr.right, scope)
        return _COMPARATORS[expr.op](left, right)
    if isinstance(expr, FilterCall):
        target = evaluate(expr.target, scope)
        args = [evaluate(a, scope) for a in expr.args]
        return apply_filter(expr.name, target, args)
    raise TypeError(f"Unknown expression node: {expr!r}")
