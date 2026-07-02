"""Write a render() result to .md files on disk."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from .errors import MdmaReferenceError

RenderedValue = Union[str, List[str], Dict[str, str]]


def write_output(
    result: Dict[str, RenderedValue],
    output_dir: Union[str, os.PathLike],
    block: Optional[str] = None,
) -> List[Path]:
    """Write one or all rendered blocks from a `render()` result to `.md` files.

    `block=None` (default) writes every top-level block; `block="name"` writes
    only that one. A string-valued block is written to `{output_dir}/{block}.md`.
    A `<multiple:>` block (list or `<name:>`-keyed dict) is written to
    `{output_dir}/{block}/`, one file per item -- `{name}.md` if the block
    declared `<name:>`, otherwise `{index}.md`.

    Raises `MdmaReferenceError` if `block` isn't a key in `result`.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if block is not None:
        if block not in result:
            raise MdmaReferenceError(f"ReferenceError: block '{block}' not found in render result")
        return _write_block(block, result[block], output_path)

    written: List[Path] = []
    for name, value in result.items():
        written.extend(_write_block(name, value, output_path))
    return written


def _write_block(name: str, value: RenderedValue, output_dir: Path) -> List[Path]:
    if isinstance(value, str):
        path = output_dir / f"{name}.md"
        path.write_text(value, encoding="utf-8")
        return [path]

    subdir = output_dir / name
    subdir.mkdir(parents=True, exist_ok=True)
    if isinstance(value, dict):
        return [_write_item(subdir, item_name, item_value) for item_name, item_value in value.items()]
    return [_write_item(subdir, str(index), item_value) for index, item_value in enumerate(value)]


def _write_item(subdir: Path, name: str, value: str) -> Path:
    resolved_subdir = subdir.resolve()
    path = (subdir / f"{name}.md").resolve()
    if not path.is_relative_to(resolved_subdir):
        raise ValueError(f"unsafe filename derived from block item name: {name!r}")
    path.write_text(value, encoding="utf-8")
    return path
