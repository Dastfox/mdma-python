"""Renders a parsed .mdma template against an inputs object into a named output map."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Union

from .errors import DuplicateNameError, MdmaTypeError
from .evaluator import Scope, evaluate
from .file_parser import parse_file
from .schema import validate_inputs
from .template_ast import ExprNode, ForNode, IfNode, Node, TextNode
from .util import format_number, to_display_string, truthy, typename

RenderedValue = Union[str, List[str], Dict[str, str]]


def render(source: str, inputs: Dict[str, Any] = None) -> Dict[str, RenderedValue]:
    """Render an .mdma source string against an inputs object.

    Returns a dict mapping each block name to its rendered string. A
    `<multiple:>` block renders to a list of strings, or -- if it also
    declares `<name:>` -- to a dict keyed by each item's computed name.
    """
    template = parse_file(source)
    resolved_inputs = validate_inputs(template.inputs, inputs or {})
    all_block_names = {block.name for block in template.blocks}

    rendered: Dict[str, RenderedValue] = {}
    for block in template.blocks:
        scope_base = Scope(rendered, resolved_inputs, all_block_names)
        if block.multiple_var:
            items = resolved_inputs.get(block.multiple_source) or []
            if block.name_expr is not None:
                named_results: Dict[str, str] = {}
                for item in items:
                    item_scope = scope_base.child({block.multiple_var: item})
                    computed_name = _stringify_name(evaluate(block.name_expr, item_scope))
                    if computed_name in named_results:
                        raise DuplicateNameError(computed_name, block.name)
                    named_results[computed_name] = _render_nodes(block.body, item_scope)
                rendered[block.name] = named_results
            else:
                results = []
                for item in items:
                    item_scope = scope_base.child({block.multiple_var: item})
                    results.append(_render_nodes(block.body, item_scope))
                rendered[block.name] = results
        else:
            rendered[block.name] = _render_nodes(block.body, scope_base)
    return rendered


def render_file(path: Union[str, os.PathLike], inputs: Dict[str, Any] = None) -> Dict[str, RenderedValue]:
    """Read `path` as UTF-8 and render it. Equivalent to `render(Path(path).read_text(), inputs)`."""
    return render(Path(path).read_text(encoding="utf-8"), inputs)


def _stringify_name(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return format_number(value)
    raise MdmaTypeError("string or number", typename(value))


def _render_nodes(nodes: List[Node], scope: Scope) -> str:
    return "".join(_render_node(node, scope) for node in nodes)


def _render_node(node: Node, scope: Scope) -> str:
    if isinstance(node, TextNode):
        return node.text
    if isinstance(node, ExprNode):
        return to_display_string(evaluate(node.expr, scope))
    if isinstance(node, IfNode):
        for condition, body in node.branches:
            if condition is None or truthy(evaluate(condition, scope)):
                return _render_nodes(body, scope)
        return ""
    if isinstance(node, ForNode):
        iterable = evaluate(node.iterable, scope)
        if iterable is None:
            iterable = []
        if not isinstance(iterable, list):
            raise MdmaTypeError("array", typename(iterable))
        parts = []
        total = len(iterable)
        for index, item in enumerate(iterable):
            loop_info = {
                "index": index + 1,
                "index0": index,
                "first": index == 0,
                "last": index == total - 1,
                "length": total,
            }
            child_scope = scope.child({node.var_name: item, "loop": loop_info})
            parts.append(_render_nodes(node.body, child_scope))
        return "".join(parts)
    raise TypeError(f"Unknown template node: {node!r}")
