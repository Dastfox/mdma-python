"""Tests for the public get_inputs / validate_inputs helpers."""

import pytest

from mdma import MdmaTypeError, MissingInputError, get_inputs, validate_inputs

SOURCE = """@inputs
title: string
count: number = 3
tags: string[] = []
draft: boolean

<body>
{title}
"""


class TestGetInputs:
    def test_returns_declared_inputs_in_order(self):
        inputs = get_inputs(SOURCE)
        assert [d.name for d in inputs] == ["title", "count", "tags", "draft"]
        assert [d.type for d in inputs] == ["string", "number", "string[]", "boolean"]

    def test_carries_defaults(self):
        by_name = {d.name: d for d in get_inputs(SOURCE)}
        assert by_name["count"].has_default and by_name["count"].default == 3
        assert by_name["tags"].has_default and by_name["tags"].default == []
        assert not by_name["title"].has_default


class TestValidateInputs:
    def test_returns_resolved_inputs_with_defaults(self):
        resolved = validate_inputs(SOURCE, {"title": "Hi", "draft": False})
        assert resolved == {"title": "Hi", "count": 3, "tags": [], "draft": False}

    def test_missing_required_input(self):
        with pytest.raises(MissingInputError):
            validate_inputs(SOURCE, {"title": "Hi"})

    def test_mistyped_input(self):
        with pytest.raises(MdmaTypeError):
            validate_inputs(SOURCE, {"title": 1, "draft": False})

    def test_ignores_undeclared_inputs(self):
        resolved = validate_inputs(SOURCE, {"title": "Hi", "draft": True, "extra": "x"})
        assert "extra" not in resolved

    def test_inputs_defaults_to_empty(self):
        source = '@inputs\nname: string = "x"\n\n<body>\n{name}\n'
        assert validate_inputs(source) == {"name": "x"}
