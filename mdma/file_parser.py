"""Parses a full .mdma source into an @inputs declaration list and blocks."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from .block_parser import parse_block_body
from .errors import MdmaSyntaxError
from .expr_parser import parse_expression
from .model import Block, InputDecl, ParsedTemplate

_INPUT_DECL_RE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*"
    r"(string\[\]|number\[\]|object\[\]|string|number|boolean|object)"
    r"\s*(?:=\s*(.+))?$"
)
# Simple, single-line header: no modifiers, e.g. "<title>".
_SIMPLE_HEADER_RE = re.compile(r"^<([A-Za-z0-9][A-Za-z0-9-]*)>$")
# Opening line of a multi-line header with modifiers: "<" alone, or "<name" with
# no closing '>' yet. The name may be inline here, or given on the next line.
_OPEN_HEADER_RE = re.compile(r"^<\s*([A-Za-z0-9][A-Za-z0-9-]*)?\s*$")
_BARE_NAME_LINE_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*)$")
_CLOSE_HEADER_RE = re.compile(r"^>\s*$")
_MULTIPLE_MOD_RE = re.compile(
    r"^multiple\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s+in\s+([A-Za-z_][A-Za-z0-9_]*)$"
)
_NAME_MOD_RE = re.compile(r"^name\s*:\s*(.+)$")

_RESERVED = {"multiple"}
_SCALAR_TYPES = {"string", "number", "boolean", "object"}


def _looks_like_block_header(stripped_line: str) -> bool:
    return bool(_SIMPLE_HEADER_RE.match(stripped_line) or _OPEN_HEADER_RE.match(stripped_line))


def parse_file(source: str) -> ParsedTemplate:
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    if not lines or lines[0].strip() != "@inputs":
        raise MdmaSyntaxError("File must begin with '@inputs' on its own line")

    idx = 1
    inputs = []
    seen_names = set()
    while idx < len(lines):
        stripped = lines[idx].strip()
        if stripped == "" or _looks_like_block_header(stripped):
            break
        decl = _parse_input_decl(stripped, idx + 1)
        if decl.name in _RESERVED:
            raise MdmaSyntaxError(
                f"'{decl.name}' is a reserved word and cannot be used as an input name"
            )
        if decl.name in seen_names:
            raise MdmaSyntaxError(f"Duplicate input declaration: '{decl.name}'")
        seen_names.add(decl.name)
        inputs.append(decl)
        idx += 1

    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1

    input_types = {decl.name: decl.type for decl in inputs}
    blocks = []
    block_names = set()

    while idx < len(lines):
        header = lines[idx].strip()
        simple_m = _SIMPLE_HEADER_RE.match(header)
        if simple_m:
            name = simple_m.group(1)
            idx += 1
            multiple_var = multiple_source = name_expr = None
        else:
            name, multiple_var, multiple_source, name_expr, idx = _parse_open_header(
                lines, idx, input_types
            )

        if name in _RESERVED:
            raise MdmaSyntaxError(
                f"'{name}' is a reserved word and cannot be used as a block name"
            )
        if name in block_names:
            raise MdmaSyntaxError(f"Duplicate block declaration: '{name}'")
        block_names.add(name)

        body_lines = []
        while idx < len(lines) and not _looks_like_block_header(lines[idx].strip()):
            body_lines.append(lines[idx])
            idx += 1
        # The blank line conventionally left between one block's content and the
        # next block's header (or EOF) is file formatting, not part of the block's
        # rendered value -- otherwise every block reference would carry a stray
        # trailing newline into whatever embeds it. Strip only the blank lines
        # touching the edges; blank lines in the middle of a body are preserved.
        body_text = "\n".join(_strip_blank_edges(body_lines))

        try:
            body_nodes = parse_block_body(body_text)
        except MdmaSyntaxError as exc:
            raise MdmaSyntaxError(f"In block '<{name}>': {exc}") from exc

        blocks.append(
            Block(
                name=name,
                multiple_var=multiple_var,
                multiple_source=multiple_source,
                name_expr=name_expr,
                body=body_nodes,
            )
        )

    if not blocks:
        raise MdmaSyntaxError("File must declare at least one block")

    return ParsedTemplate(inputs=inputs, blocks=blocks)


def _parse_open_header(
    lines: List[str], idx: int, input_types: Dict[str, str]
) -> Tuple[str, Optional[str], Optional[str], object, int]:
    """Parses a multi-line block header, e.g.::

        <changelog-entry
        multiple: entry in releases
        name: entry.version
        >

    The name may also be given alone on the line right after `<`::

        <
        changelog-entry
        multiple: entry in releases
        >

    `multiple` and `name` may appear in either order; `name` requires `multiple`.
    Returns (name, multiple_var, multiple_source, name_expr, next_idx).
    """
    om = _OPEN_HEADER_RE.match(lines[idx].strip())
    if not om:
        raise MdmaSyntaxError(
            f"Expected a block header ('<name>') at line {idx + 1}, got: {lines[idx]!r}"
        )
    name = om.group(1)
    idx += 1

    if name is None:
        if idx >= len(lines):
            raise MdmaSyntaxError("Unterminated block header: expected a block name")
        nm = _BARE_NAME_LINE_RE.match(lines[idx].strip())
        if not nm:
            raise MdmaSyntaxError(f"Expected a block name at line {idx + 1}, got: {lines[idx]!r}")
        name = nm.group(1)
        idx += 1

    multiple_var: Optional[str] = None
    multiple_source: Optional[str] = None
    name_expr_raw: Optional[str] = None
    seen = set()
    while True:
        if idx >= len(lines):
            raise MdmaSyntaxError(f"Unterminated block header for '<{name}>': missing closing '>'")
        line = lines[idx].strip()
        if _CLOSE_HEADER_RE.match(line):
            idx += 1
            break
        if line == "":
            raise MdmaSyntaxError(
                f"Unterminated block header for '<{name}>': blank line before closing '>'"
            )
        mm = _MULTIPLE_MOD_RE.match(line)
        if mm:
            if "multiple" in seen:
                raise MdmaSyntaxError(f"Block '<{name}>' declares 'multiple' more than once")
            seen.add("multiple")
            multiple_var, multiple_source = mm.group(1), mm.group(2)
            idx += 1
            continue
        nmm = _NAME_MOD_RE.match(line)
        if nmm:
            if "name" in seen:
                raise MdmaSyntaxError(f"Block '<{name}>' declares 'name' more than once")
            seen.add("name")
            name_expr_raw = nmm.group(1)
            idx += 1
            continue
        raise MdmaSyntaxError(f"Unknown block modifier at line {idx + 1}: {lines[idx]!r}")

    if name_expr_raw is not None and multiple_var is None:
        raise MdmaSyntaxError(f"Block '<{name}>': 'name' modifier requires a 'multiple' modifier")

    if multiple_var is not None:
        if multiple_source not in input_types:
            raise MdmaSyntaxError(
                f"Block '<{name}>' multiple modifier references unknown input '{multiple_source}'"
            )
        if not input_types[multiple_source].endswith("[]"):
            raise MdmaSyntaxError(
                f"Block '<{name}>' multiple modifier requires an array input, "
                f"but '{multiple_source}' is '{input_types[multiple_source]}'"
            )

    name_expr = parse_expression(name_expr_raw) if name_expr_raw is not None else None
    return name, multiple_var, multiple_source, name_expr, idx


def _strip_blank_edges(lines):
    start = 0
    end = len(lines)
    while start < end and lines[start].strip() == "":
        start += 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    return lines[start:end]


def _parse_input_decl(stripped: str, line_no: int) -> InputDecl:
    m = _INPUT_DECL_RE.match(stripped)
    if not m:
        raise MdmaSyntaxError(f"Invalid input declaration at line {line_no}: {stripped!r}")
    name, type_, default_raw = m.group(1), m.group(2), m.group(3)
    if default_raw is None:
        return InputDecl(name=name, type=type_, has_default=False, default=None)
    default_value = _parse_default(default_raw.strip(), type_, line_no)
    return InputDecl(name=name, type=type_, has_default=True, default=default_value)


def _parse_default(raw: str, type_: str, line_no: int):
    if raw == "[]":
        return []
    if raw == '""':
        return ""
    if raw in ("true", "false"):
        return raw == "true"
    if re.match(r"^-?\d+(\.\d+)?$", raw):
        return float(raw) if "." in raw else int(raw)
    if raw.startswith('"') and raw.endswith('"'):
        return json.loads(raw)
    raise MdmaSyntaxError(f"Invalid default value at line {line_no}: {raw!r}")
