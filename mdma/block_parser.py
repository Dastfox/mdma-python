"""Tokenizes a block body into text/expr/tag spans, applies whitespace control,
and builds the nested if/for AST.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .errors import MdmaSyntaxError
from .expr_parser import parse_expression
from .template_ast import ExprNode, ForNode, IfNode, Node, TextNode

_TAG_SPAN_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.DOTALL)

_IF_RE = re.compile(r"^if\s+(.+)$", re.DOTALL)
_ELIF_RE = re.compile(r"^elif\s+(.+)$", re.DOTALL)
_ELSE_RE = re.compile(r"^else$")
_ENDIF_RE = re.compile(r"^endif$")
_FOR_RE = re.compile(r"^for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+(.+)$", re.DOTALL)
_ENDFOR_RE = re.compile(r"^endfor$")


@dataclass
class _RawToken:
    kind: str  # 'text' | 'expr' | 'tag' | 'comment'
    content: str
    trim_left: bool = False
    trim_right: bool = False


def _split_delims(raw_inner: str) -> Tuple[str, bool, bool]:
    trim_left = raw_inner.startswith("-")
    body = raw_inner[1:] if trim_left else raw_inner
    trim_right = body.endswith("-")
    if trim_right:
        body = body[:-1]
    return body.strip(), trim_left, trim_right


def tokenize_body(body: str) -> List[_RawToken]:
    tokens: List[_RawToken] = []
    pos = 0
    for m in _TAG_SPAN_RE.finditer(body):
        if m.start() > pos:
            tokens.append(_RawToken("text", body[pos : m.start()]))
        raw = m.group(0)
        inner = raw[2:-2]
        content, trim_left, trim_right = _split_delims(inner)
        if raw.startswith("{{"):
            kind = "expr"
        elif raw.startswith("{%"):
            kind = "tag"
        else:
            kind = "comment"
        tokens.append(_RawToken(kind, content, trim_left, trim_right))
        pos = m.end()
    if pos < len(body):
        tokens.append(_RawToken("text", body[pos:]))
    for tok in tokens:
        if tok.kind == "text" and "{#" in tok.content:
            raise MdmaSyntaxError("Unclosed comment: missing '#}'")
    return tokens


# A comment is "standalone" when nothing but whitespace shares its line; the
# whole line then vanishes from the output, so authors can annotate templates
# without leaving blank lines behind.
# \Z, not $: $ would also match before a trailing newline, hiding the
# newline-anchored match that proves the comment starts its own line.
_STANDALONE_LEFT_RE = re.compile(r"(^|\n)[ \t]*\Z")
_STANDALONE_RIGHT_RE = re.compile(r"^[ \t]*\n")
_ONLY_INDENT_RE = re.compile(r"^[ \t]*\Z")


def strip_comment_lines(tokens: List[_RawToken]) -> List[_RawToken]:
    tokens = list(tokens)

    # Decide standalone-ness on the untouched token stream first: removals
    # mutate the very text tokens the line-position checks rely on.
    plans = []  # (comment index, 'newline' | 'eof')
    for i, tok in enumerate(tokens):
        if tok.kind != "comment":
            continue
        if i > 0:
            prev = tokens[i - 1]
            if prev.kind != "text":
                continue
            m = _STANDALONE_LEFT_RE.search(prev.content)
            # A match on '^' only proves line-start if the text token itself
            # opens the body; otherwise another tag sits on the same line.
            if not m or (m.group(1) == "" and i != 1):
                continue
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if nxt is None:
            plans.append((i, "eof"))
        elif nxt.kind == "text" and _STANDALONE_RIGHT_RE.match(nxt.content):
            plans.append((i, "newline"))
        elif nxt.kind == "text" and i + 2 == len(tokens) and _ONLY_INDENT_RE.match(nxt.content):
            plans.append((i, "eof"))

    for i, mode in plans:
        if i > 0:
            prev = tokens[i - 1]
            # 'eof': the comment is the last line, so the line it vanishes
            # with includes the newline that started it.
            pattern = r"\n?[ \t]*$" if mode == "eof" else r"[ \t]*$"
            tokens[i - 1] = _RawToken("text", re.sub(pattern, "", prev.content, count=1))
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if mode == "newline":
                content = _STANDALONE_RIGHT_RE.sub("", nxt.content, count=1)
            else:
                content = ""
            tokens[i + 1] = _RawToken("text", content)
    return tokens


def drop_comments(tokens: List[_RawToken]) -> List[_RawToken]:
    """Removes comment tokens, honoring their trim markers, and merges the
    text tokens left adjacent so later whitespace control sees the same
    stream it would have without the comment."""
    result: List[_RawToken] = []
    pending_trim = False
    for tok in tokens:
        if tok.kind == "comment":
            if tok.trim_left and result and result[-1].kind == "text":
                result[-1] = _RawToken("text", result[-1].content.rstrip())
            pending_trim = pending_trim or tok.trim_right
            continue
        if tok.kind == "text":
            content = tok.content.lstrip() if pending_trim else tok.content
            pending_trim = False
            if result and result[-1].kind == "text":
                result[-1] = _RawToken("text", result[-1].content + content)
            else:
                result.append(_RawToken("text", content))
            continue
        pending_trim = False
        result.append(tok)
    return result


def apply_whitespace_control(tokens: List[_RawToken]) -> List[_RawToken]:
    tokens = list(tokens)
    for i, tok in enumerate(tokens):
        if tok.kind == "text":
            continue
        if tok.trim_left and i > 0 and tokens[i - 1].kind == "text":
            tokens[i - 1] = _RawToken("text", tokens[i - 1].content.rstrip())
        if tok.trim_right and i + 1 < len(tokens) and tokens[i + 1].kind == "text":
            tokens[i + 1] = _RawToken("text", tokens[i + 1].content.lstrip())
    return tokens


def _classify_tag(stmt: str) -> Optional[str]:
    if _IF_RE.match(stmt):
        return "if"
    if _ELIF_RE.match(stmt):
        return "elif"
    if _ELSE_RE.match(stmt):
        return "else"
    if _ENDIF_RE.match(stmt):
        return "endif"
    if _FOR_RE.match(stmt):
        return "for"
    if _ENDFOR_RE.match(stmt):
        return "endfor"
    return None


def parse_nodes(
    tokens: List[_RawToken], start: int, stop_kinds: Tuple[str, ...]
) -> Tuple[List[Node], int]:
    nodes: List[Node] = []
    i = start
    while i < len(tokens):
        tok = tokens[i]
        if tok.kind == "tag":
            kind = _classify_tag(tok.content)
            if kind in stop_kinds:
                return nodes, i
            if kind == "if":
                node, i = _parse_if(tokens, i)
                nodes.append(node)
                continue
            if kind == "for":
                node, i = _parse_for(tokens, i)
                nodes.append(node)
                continue
            raise MdmaSyntaxError(f"Unexpected tag: {{% {tok.content} %}}")
        if tok.kind == "text":
            if tok.content:
                nodes.append(TextNode(tok.content))
            i += 1
            continue
        # expr
        nodes.append(ExprNode(parse_expression(tok.content)))
        i += 1
    return nodes, i


def _parse_if(tokens: List[_RawToken], i: int) -> Tuple[IfNode, int]:
    m = _IF_RE.match(tokens[i].content)
    assert m is not None
    cond = parse_expression(m.group(1))
    body, i = parse_nodes(tokens, i + 1, ("elif", "else", "endif"))
    branches = [(cond, body)]

    while i < len(tokens) and _classify_tag(tokens[i].content) == "elif":
        em = _ELIF_RE.match(tokens[i].content)
        assert em is not None
        cond2 = parse_expression(em.group(1))
        body2, i = parse_nodes(tokens, i + 1, ("elif", "else", "endif"))
        branches.append((cond2, body2))

    if i < len(tokens) and _classify_tag(tokens[i].content) == "else":
        else_body, i = parse_nodes(tokens, i + 1, ("endif",))
        branches.append((None, else_body))

    if not (i < len(tokens) and _classify_tag(tokens[i].content) == "endif"):
        raise MdmaSyntaxError("Missing {% endif %}")
    i += 1
    return IfNode(branches), i


def _parse_for(tokens: List[_RawToken], i: int) -> Tuple[ForNode, int]:
    m = _FOR_RE.match(tokens[i].content)
    assert m is not None
    var_name = m.group(1)
    iterable = parse_expression(m.group(2))
    body, i = parse_nodes(tokens, i + 1, ("endfor",))
    if not (i < len(tokens) and _classify_tag(tokens[i].content) == "endfor"):
        raise MdmaSyntaxError("Missing {% endfor %}")
    i += 1
    return ForNode(var_name, iterable, body), i


def parse_block_body(body: str) -> List[Node]:
    tokens = drop_comments(strip_comment_lines(tokenize_body(body)))
    tokens = apply_whitespace_control(tokens)
    nodes, end = parse_nodes(tokens, 0, ())
    if end != len(tokens):
        stray = tokens[end].content if tokens[end].kind == "tag" else tokens[end]
        raise MdmaSyntaxError(f"Unmatched control tag: {{% {stray} %}}")
    return nodes
