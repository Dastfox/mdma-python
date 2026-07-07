"""{# ... #} comments: stripped at parse time, never rendered."""

import pytest

from mdma import render
from mdma.errors import MdmaSyntaxError


def test_inline_comment_is_stripped():
    src = "@inputs\nname: string\n<out>\nHello {# note #}world\n"
    assert render(src, {"name": "x"})["out"] == "Hello world"


def test_full_line_comment_vanishes_with_its_line():
    src = "@inputs\nname: string\n<out>\nline one\n{# gone #}\nline two\n"
    assert render(src, {"name": "x"})["out"] == "line one\nline two"


def test_indented_full_line_comment_vanishes():
    src = "@inputs\nname: string\n<out>\nline one\n   {# gone #}   \nline two\n"
    assert render(src, {"name": "x"})["out"] == "line one\nline two"


def test_consecutive_full_line_comments():
    src = "@inputs\nname: string\n<out>\nline one\n{# a #}\n{# b #}\nline two\n"
    assert render(src, {"name": "x"})["out"] == "line one\nline two"


def test_multiline_comment_at_end_of_body():
    src = "@inputs\nname: string\n<out>\nline one\n{# spans\nseveral\nlines #}\n"
    assert render(src, {"name": "x"})["out"] == "line one"


def test_commented_out_template_code_is_not_evaluated():
    src = "@inputs\nname: string\n<out>\n{{ name }}{# {{ missing_var }} {% if broken %} #}\n"
    assert render(src, {"name": "x"})["out"] == "x"


def test_comment_trim_markers():
    src = "@inputs\nname: string\n<out>\na  {#- note -#}  b\n"
    assert render(src, {"name": "x"})["out"] == "ab"


def test_comment_ends_at_first_closer():
    src = "@inputs\nname: string\n<out>\nx{# a #} b #}\n"
    assert render(src, {"name": "x"})["out"] == "x b #}"


def test_comment_line_inside_for_loop():
    src = (
        "@inputs\nitems: string[] = []\n<out>\n"
        "{% for item in items -%}\n"
        "{# per-item note #}\n"
        "- {{ item }}\n"
        "{% endfor %}"
    )
    assert render(src, {"items": ["a", "b"]})["out"] == "- a\n- b\n"


def test_comment_only_body_renders_empty():
    src = "@inputs\nname: string\n<out>\n{# nothing to see #}\n"
    assert render(src, {"name": "x"})["out"] == ""


def test_comments_in_inputs_section():
    src = (
        "@inputs\n"
        "{# who is greeted #}\n"
        "name: string\n"
        "count: number = 2  {# how many times #}\n"
        "<out>\n"
        "{{ name }} x{{ count }}\n"
    )
    assert render(src, {"name": "bob"})["out"] == "bob x2"


def test_comment_like_span_inside_quoted_default_is_preserved():
    src = '@inputs\nnote: string = "keep {# this #}"\n<out>\n{{ note }}\n'
    assert render(src, {})["out"] == "keep {# this #}"


def test_comment_lines_between_blocks():
    src = (
        "@inputs\n"
        "name: string\n"
        "\n"
        "{# separator before the first block #}\n"
        "<first>\n"
        "{{ name }}\n"
        "\n"
        "{# separator between blocks #}\n"
        "\n"
        "<second>\n"
        "{{ first }}!\n"
    )
    result = render(src, {"name": "bob"})
    assert result["first"] == "bob"
    assert result["second"] == "bob!"


def test_literal_comment_delimiter_via_interpolation():
    src = '@inputs\nname: string\n<out>\n{{ "{#" }}comment{{ "#}" }}\n'
    assert render(src, {"name": "x"})["out"] == "{#comment#}"


def test_unclosed_comment_raises():
    src = "@inputs\nname: string\n<out>\noops {# never closed\n"
    with pytest.raises(MdmaSyntaxError):
        render(src, {"name": "x"})


def test_unclosed_comment_in_inputs_raises():
    src = "@inputs\n{# oops\nname: string\n<out>\nhi\n"
    with pytest.raises(MdmaSyntaxError):
        render(src, {"name": "x"})
