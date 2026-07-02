"""Tokenizer and recursive-descent parser for expressions inside {{ }} / {% %}.

Precedence, low to high: or > and > not > comparison > filter (|) > primary.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from .errors import MdmaSyntaxError
from .template_ast import ArrayLiteral, BinOp, Expr, FilterCall, Literal, Not, Var

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"'
    r"|-?\d+(?:\.\d+)?"
    r"|==|!=|>=|<="
    r"|[><|,().\[\]]"
    r"|[A-Za-z_][A-Za-z0-9_]*"
)

_COMPARATORS = {"==", "!=", ">", ">=", "<", "<="}


@dataclass
class Token:
    kind: str  # 'string' | 'number' | 'op' | 'ident'
    value: str


def tokenize(src: str) -> List[Token]:
    tokens: List[Token] = []
    pos = 0
    n = len(src)
    while pos < n:
        ws = _WS_RE.match(src, pos)
        if ws:
            pos = ws.end()
            if pos >= n:
                break
        m = _TOKEN_RE.match(src, pos)
        if not m:
            raise MdmaSyntaxError(
                f"Unexpected character in expression: {src[pos:pos + 20]!r}"
            )
        text = m.group(0)
        if text[0] == '"':
            tokens.append(Token("string", text))
        elif text[0].isdigit() or (text[0] == "-" and len(text) > 1):
            tokens.append(Token("number", text))
        elif text in _COMPARATORS or text in "><|,().[]":
            tokens.append(Token("op", text))
        else:
            tokens.append(Token("ident", text))
        pos = m.end()
    return tokens


class _Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self) -> Optional[Token]:
        t = self.peek()
        self.pos += 1
        return t

    def _is_op(self, value: str) -> bool:
        t = self.peek()
        return t is not None and t.kind == "op" and t.value == value

    def expect_op(self, value: str) -> Token:
        t = self.advance()
        if t is None or t.kind != "op" or t.value != value:
            raise MdmaSyntaxError(f"Expected '{value}' in expression")
        return t

    def match_ident(self, keyword: str) -> bool:
        t = self.peek()
        if t is not None and t.kind == "ident" and t.value == keyword:
            self.advance()
            return True
        return False

    def parse(self) -> Expr:
        expr = self.parse_or()
        if self.pos != len(self.tokens):
            raise MdmaSyntaxError(f"Unexpected token in expression: {self.peek()}")
        return expr

    def parse_or(self) -> Expr:
        left = self.parse_and()
        while self.match_ident("or"):
            right = self.parse_and()
            left = BinOp("or", left, right)
        return left

    def parse_and(self) -> Expr:
        left = self.parse_not()
        while self.match_ident("and"):
            right = self.parse_not()
            left = BinOp("and", left, right)
        return left

    def parse_not(self) -> Expr:
        if self.match_ident("not"):
            return Not(self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self) -> Expr:
        left = self.parse_filter_expr()
        t = self.peek()
        if t is not None and t.kind == "op" and t.value in _COMPARATORS:
            self.advance()
            right = self.parse_filter_expr()
            return BinOp(t.value, left, right)
        return left

    def parse_filter_expr(self) -> Expr:
        expr = self.parse_primary()
        while self._is_op("|"):
            self.advance()
            name_tok = self.advance()
            if name_tok is None or name_tok.kind != "ident":
                raise MdmaSyntaxError("Expected filter name after '|'")
            args: List[Expr] = []
            if self._is_op("("):
                self.advance()
                if not self._is_op(")"):
                    args.append(self.parse_or())
                    while self._is_op(","):
                        self.advance()
                        args.append(self.parse_or())
                self.expect_op(")")
            expr = FilterCall(expr, name_tok.value, args)
        return expr

    def parse_primary(self) -> Expr:
        t = self.advance()
        if t is None:
            raise MdmaSyntaxError("Unexpected end of expression")
        if t.kind == "string":
            return Literal(json.loads(t.value))
        if t.kind == "number":
            return Literal(float(t.value) if "." in t.value else int(t.value))
        if t.kind == "op" and t.value == "[":
            items: List[Expr] = []
            if not self._is_op("]"):
                items.append(self.parse_or())
                while self._is_op(","):
                    self.advance()
                    items.append(self.parse_or())
            self.expect_op("]")
            return ArrayLiteral(items)
        if t.kind == "ident":
            if t.value == "true":
                return Literal(True)
            if t.value == "false":
                return Literal(False)
            path = [t.value]
            while self._is_op("."):
                self.advance()
                nxt = self.advance()
                if nxt is None or nxt.kind != "ident":
                    raise MdmaSyntaxError("Expected identifier after '.'")
                path.append(nxt.value)
            return Var(path)
        raise MdmaSyntaxError(f"Unexpected token in expression: {t}")


def parse_expression(src: str) -> Expr:
    if not src.strip():
        raise MdmaSyntaxError("Empty expression")
    return _Parser(tokenize(src)).parse()
