import pytest

from mdma import render
from mdma.errors import DuplicateNameError, MdmaSyntaxError, MdmaTypeError


def test_if_elif_else():
    src = (
        "@inputs\n"
        "n: number\n"
        "<out>\n"
        "{% if n > 10 %}big{% elif n > 0 %}small{% else %}non-positive{% endif %}\n"
    )
    assert render(src, {"n": 20})["out"].strip() == "big"
    assert render(src, {"n": 5})["out"].strip() == "small"
    assert render(src, {"n": -1})["out"].strip() == "non-positive"


def test_logical_operators():
    src = (
        "@inputs\n"
        "a: boolean = false\n"
        "b: boolean = false\n"
        "<out>\n"
        "{% if a and b %}both{% elif a or b %}one{% else %}neither{% endif %}\n"
    )
    assert render(src, {"a": True, "b": True})["out"].strip() == "both"
    assert render(src, {"a": True, "b": False})["out"].strip() == "one"
    assert render(src, {"a": False, "b": False})["out"].strip() == "neither"


def test_not_operator():
    src = "@inputs\nflag: boolean = false\n<out>\n{% if not flag %}yes{% else %}no{% endif %}\n"
    assert render(src, {"flag": False})["out"].strip() == "yes"
    assert render(src, {"flag": True})["out"].strip() == "no"


def test_nested_if_and_for():
    src = (
        "@inputs\n"
        "items: string[] = []\n"
        "<out>\n"
        "{% for item in items -%}\n"
        "{% if loop.first %}[{% endif %}{{ item }}{% if not loop.last %}, {% endif %}"
        "{% if loop.last %}]{% endif %}\n"
        "{%- endfor %}"
    )
    result = render(src, {"items": ["a", "b", "c"]})
    assert result["out"] == "[a, b, c]"


def test_loop_variables():
    src = (
        "@inputs\n"
        "items: string[] = []\n"
        "<out>\n"
        "{% for item in items -%}\n"
        "{{ loop.index }}:{{ loop.index0 }}:{{ loop.length }} "
        "{% endfor %}"
    )
    result = render(src, {"items": ["x", "y"]})
    assert result["out"] == "1:0:2 2:1:2 "


def test_whitespace_control_matches_spec_5_3_example():
    src = (
        "@inputs\n"
        "breaking: boolean = false\n"
        "<out>\n"
        "before\n"
        "{%- if breaking %}\n"
        "\n"
        "> **Breaking changes included in this release.**\n"
        "{%- endif %}\n"
        "after"
    )
    with_breaking = render(src, {"breaking": True})["out"]
    without_breaking = render(src, {"breaking": False})["out"]
    assert with_breaking == "before\n\n> **Breaking changes included in this release.**\nafter"
    assert without_breaking == "before\nafter"


def test_multiple_modifier_produces_array():
    src = (
        "@inputs\n"
        "releases: object[] = []\n"
        "<entry\n"
        "multiple: r in releases\n"
        ">\n"
        "{{ r.version }}\n"
    )
    result = render(src, {"releases": [{"version": "1.0"}, {"version": "2.0"}]})
    assert result["entry"] == ["1.0", "2.0"]


def test_multiple_modifier_empty_array():
    src = "@inputs\nreleases: object[] = []\n<entry\nmultiple: r in releases\n>\n{{ r.version }}\n"
    result = render(src, {"releases": []})
    assert result["entry"] == []


def test_multiple_modifier_with_open_angle_alone_and_name_on_next_line():
    src = (
        "@inputs\nreleases: object[] = []\n<\nentry\nmultiple: r in releases\n>\n{{ r.version }}\n"
    )
    result = render(src, {"releases": [{"version": "1.0"}]})
    assert result["entry"] == ["1.0"]


def test_name_modifier_produces_object_keyed_by_computed_name():
    src = (
        "@inputs\nreleases: object[] = []\n<entry\n"
        "multiple: r in releases\nname: r.version\n>\n{{ r.date }}\n"
    )
    result = render(
        src,
        {
            "releases": [
                {"version": "2.1.0", "date": "2026-06-01"},
                {"version": "2.0.0", "date": "2026-05-01"},
            ]
        },
    )
    assert result["entry"] == {"2.1.0": "2026-06-01", "2.0.0": "2026-05-01"}


def test_name_modifier_may_precede_multiple_modifier():
    src = (
        "@inputs\nreleases: object[] = []\n<entry\n"
        "name: r.version\nmultiple: r in releases\n>\n{{ r.date }}\n"
    )
    result = render(src, {"releases": [{"version": "2.1.0", "date": "2026-06-01"}]})
    assert result["entry"] == {"2.1.0": "2026-06-01"}


def test_name_modifier_with_empty_array_produces_empty_object():
    src = (
        "@inputs\nreleases: object[] = []\n<entry\n"
        "multiple: r in releases\nname: r.version\n>\n{{ r.date }}\n"
    )
    result = render(src, {"releases": []})
    assert result["entry"] == {}


def test_name_modifier_numeric_name_is_stringified():
    src = (
        "@inputs\nitems: object[] = []\n<entry\n"
        "multiple: it in items\nname: it.id\n>\n{{ it.label }}\n"
    )
    result = render(src, {"items": [{"id": 1, "label": "a"}, {"id": 2, "label": "b"}]})
    assert result["entry"] == {"1": "a", "2": "b"}


def test_name_modifier_duplicate_names_raise():
    src = (
        "@inputs\nitems: object[] = []\n<entry\n"
        "multiple: it in items\nname: it.id\n>\n{{ it.label }}\n"
    )
    with pytest.raises(DuplicateNameError) as exc_info:
        render(src, {"items": [{"id": "x", "label": "a"}, {"id": "x", "label": "b"}]})
    assert str(exc_info.value) == "DuplicateName: 'x' in block 'entry'"


def test_name_modifier_non_scalar_name_raises_type_error():
    src = (
        "@inputs\nitems: object[] = []\n<entry\n"
        "multiple: it in items\nname: it.tags\n>\n{{ it.label }}\n"
    )
    with pytest.raises(MdmaTypeError):
        render(src, {"items": [{"tags": ["a", "b"], "label": "x"}]})


def test_name_modifier_without_multiple_is_syntax_error():
    src = "@inputs\nflag: boolean = false\n<out\nname: flag\n>\nhi\n"
    with pytest.raises(MdmaSyntaxError):
        render(src, {})


def test_duplicate_multiple_modifier_is_syntax_error():
    src = (
        "@inputs\nreleases: object[] = []\n<entry\n"
        "multiple: r in releases\nmultiple: r in releases\n>\n{{ r.version }}\n"
    )
    with pytest.raises(MdmaSyntaxError):
        render(src, {"releases": []})


def test_unterminated_block_header_is_syntax_error():
    src = "@inputs\nreleases: object[] = []\n<entry\nmultiple: r in releases\n{{ r.version }}\n"
    with pytest.raises(MdmaSyntaxError):
        render(src, {"releases": []})


def test_dangling_endif_is_syntax_error():
    src = "@inputs\nflag: boolean = false\n<out>\n{% endif %}\n"
    with pytest.raises(MdmaSyntaxError):
        render(src, {})


def test_missing_endfor_is_syntax_error():
    src = "@inputs\nitems: string[] = []\n<out>\n{% for x in items %}{{ x }}\n"
    with pytest.raises(MdmaSyntaxError):
        render(src, {"items": []})
