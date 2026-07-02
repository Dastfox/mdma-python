import pytest

from mdma import render
from mdma.errors import FilterError


def _render_expr(expr: str, extra_input_decls: str = "") -> str:
    source = f"@inputs\n{extra_input_decls}<out>\n{{{{ {expr} }}}}\n"
    return render(source, {})["out"]


def test_length_string_and_array():
    assert _render_expr('"hello" | length') == "5"
    src = "@inputs\ntags: string[] = []\n<out>\n{{ tags | length }}\n"
    assert render(src, {"tags": ["a", "b", "c"]})["out"] == "3"


def test_lower_upper_trim():
    assert _render_expr('"HeLLo" | lower') == "hello"
    assert _render_expr('"HeLLo" | upper') == "HELLO"
    assert _render_expr('"  hi  " | trim') == "hi"


def test_join_default_and_custom_separator():
    src = '@inputs\ntags: string[] = []\n<out>\n{{ tags | join(", ") }}\n'
    assert render(src, {"tags": ["a", "b"]})["out"] == "a, b"
    src2 = "@inputs\ntags: string[] = []\n<out>\n{{ tags | join }}\n"
    assert render(src2, {"tags": ["a", "b"]})["out"] == "ab"


def test_first_last_on_empty_array_returns_nothing():
    src = '@inputs\ntags: string[] = []\n<out>\n{{ tags | first | default("none") }}\n'
    assert render(src, {"tags": []})["out"] == "none"
    src2 = '@inputs\ntags: string[] = []\n<out>\n{{ tags | last | default("none") }}\n'
    assert render(src2, {"tags": []})["out"] == "none"


def test_first_last_nonempty():
    src = "@inputs\ntags: string[] = []\n<out>\n{{ tags | first }}-{{ tags | last }}\n"
    assert render(src, {"tags": ["a", "b", "c"]})["out"] == "a-c"


def test_default_on_missing_object_property():
    src = '@inputs\nitem: object\n<out>\n{{ item.description | default("N/A") }}\n'
    assert render(src, {"item": {}})["out"] == "N/A"
    assert render(src, {"item": {"description": "hi"}})["out"] == "hi"


def test_default_on_empty_array_literal():
    src = "@inputs\ntags: string[] = []\n<out>\n{{ tags | default([]) | length }}\n"
    assert render(src, {"tags": []})["out"] == "0"


def test_reverse_string_and_array():
    assert _render_expr('"abc" | reverse') == "cba"
    src = '@inputs\ntags: string[] = []\n<out>\n{{ tags | reverse | join(",") }}\n'
    assert render(src, {"tags": ["a", "b", "c"]})["out"] == "c,b,a"


def test_sort_and_unique():
    src = '@inputs\ntags: string[] = []\n<out>\n{{ tags | sort | unique | join(", ") }}\n'
    assert render(src, {"tags": ["beta", "api", "beta", "stable"]})["out"] == "api, beta, stable"


def test_chained_filters():
    src = "@inputs\nname: string\n<out>\n{{ name | lower | trim }}\n"
    assert render(src, {"name": "  ACME  "})["out"] == "acme"


@pytest.mark.parametrize(
    "expr, filter_name",
    [
        ("123 | length", "length"),
        ("123 | lower", "lower"),
        ("123 | upper", "upper"),
        ("123 | trim", "trim"),
        ('"x" | join(",")', "join"),
        ('"x" | first', "first"),
        ('"x" | last', "last"),
        ('"x" | sort', "sort"),
        ('"x" | unique', "unique"),
        ('"x" | reverse', None),  # reverse accepts strings too -- should NOT raise
    ],
)
def test_filter_type_errors(expr, filter_name):
    if filter_name is None:
        _render_expr(expr)  # must not raise
        return
    with pytest.raises(FilterError) as exc_info:
        _render_expr(expr)
    assert exc_info.value.filter_name == filter_name


def test_unknown_filter_raises_syntax_error():
    from mdma.errors import MdmaSyntaxError

    with pytest.raises(MdmaSyntaxError):
        _render_expr('"x" | notafilter')
