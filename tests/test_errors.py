import pytest

from mdma import render
from mdma.errors import MdmaReferenceError, MdmaTypeError, MissingInputError


def test_missing_required_input():
    src = "@inputs\nname: string\n<out>\n{{ name }}\n"
    with pytest.raises(MissingInputError) as exc_info:
        render(src, {})
    assert str(exc_info.value) == "MissingInput: name"
    assert exc_info.value.name == "name"


def test_input_type_mismatch():
    src = "@inputs\ncount: number\n<out>\n{{ count }}\n"
    with pytest.raises(MdmaTypeError) as exc_info:
        render(src, {"count": "not a number"})
    assert str(exc_info.value) == "TypeError: expected number, got string"


def test_array_input_type_mismatch():
    src = "@inputs\ntags: string[] = []\n<out>\n{{ tags }}\n"
    with pytest.raises(MdmaTypeError):
        render(src, {"tags": "not an array"})


def test_array_item_type_mismatch():
    src = "@inputs\ntags: string[] = []\n<out>\n{{ tags }}\n"
    with pytest.raises(MdmaTypeError):
        render(src, {"tags": ["ok", 5]})


def test_forward_block_reference():
    src = "@inputs\nname: string\n<a>\n{{ b }}\n<b>\n{{ name }}\n"
    with pytest.raises(MdmaReferenceError) as exc_info:
        render(src, {"name": "x"})
    assert str(exc_info.value) == "ReferenceError: block 'b' not yet rendered"


def test_undefined_variable_reference():
    src = "@inputs\nname: string\n<out>\n{{ nope }}\n"
    with pytest.raises(MdmaReferenceError) as exc_info:
        render(src, {"name": "x"})
    assert str(exc_info.value) == "ReferenceError: 'nope' is not defined"


def test_backward_block_reference_is_allowed():
    src = "@inputs\nname: string\n<a>\n{{ name }}\n<b>\n{{ a }}!\n"
    result = render(src, {"name": "hi"})
    assert result["a"] == "hi"
    assert result["b"] == "hi!"


def test_block_reference_resolves_before_same_named_input():
    # Resolution order: previously rendered blocks first, then inputs. A block
    # named the same as an input cannot reference itself (it isn't rendered
    # yet), but a later block referencing that name gets the block's output.
    src = "@inputs\ntitle: string\n<title>\nCustom Title\n<out>\n{{ title }}\n"
    result = render(src, {"title": "Report"})
    assert result["title"] == "Custom Title"
    assert result["out"] == "Custom Title"
