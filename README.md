# python-mdma

Render one or more Markdown strings from an `.mdma` template and a typed inputs object.

This is the Python reference implementation of [MDMA](https://github.com/Dastfox/mdma). See the [language specification and docs](https://dastfox.github.io/mdma/) for the full grammar, filter reference, and worked examples.

## Install

```bash
pip install -e .
```

## Usage

```python
from mdma import render

source = open("release-notes.mdma").read()
result = render(source, {
    "project": "Acme SDK",
    "version": "3.0.0",
    "date": "2026-07-01",
    "added": ["WebSocket support"],
    "breaking": True,
    "releases": [{"version": "2.1.0", "date": "2026-06-01", "added": ["Dark mode"]}],
})

result["slug"]             # "Acme SDK-3.0.0"          (str)
result["release-notes"]    # rendered markdown          (str)
result["changelog-entry"]  # one string per release     (list[str], from `<multiple:>`)
```

A `<multiple:>` block can also declare `<name:>` to key each item by a computed
name instead of array position:

```mdma
<changelog-by-version>
<multiple: entry in releases>
<name: entry.version>

### {{ entry.version }} — {{ entry.date }}
```

```python
result["changelog-by-version"]
# {"2.1.0": "### 2.1.0 — 2026-06-01\n", "2.0.0": "### 2.0.0 — 2026-05-01\n"}
```

`render_template(template, inputs)` renders an already-parsed template (from
`parse_file`) — same semantics as `render`, minus the parse:

```python
from mdma import parse_file, render_template

template = parse_file(source)  # parse once ...
render_template(template, {"project": "Acme SDK", "version": "3.0.0", "date": "2026-07-01"})  # ... render many times
```

`render_file(path, inputs)` reads `path` as UTF-8 and renders it — equivalent
to `render(open(path).read(), inputs)`:

```python
from mdma import render_file

result = render_file("release-notes.mdma", {"project": "Acme SDK", "version": "3.0.0", "date": "2026-07-01"})
```

`write_output(result, output_dir, block=None)` writes a `render()`/`render_file()`
result to `.md` files. Omit `block` to write every top-level block; pass a
block name to write only that one. A string-valued block becomes
`{output_dir}/{block}.md`; a `<multiple:>` block becomes a directory
`{output_dir}/{block}/` with one file per item — `{name}.md` if the block
declared `<name:>`, otherwise `{index}.md`. Returns the list of `Path`s written.

```python
from mdma import render_file, write_output

result = render_file("release-notes.mdma", {...})
write_output(result, "out/")                        # every block
write_output(result, "out/", block="release-notes")  # just that one
```

`get_inputs(source)` returns the template's `@inputs` declarations, and
`validate_inputs(source, inputs)` checks an inputs dict against them without
rendering — returning the resolved inputs (defaults applied) or raising
`MissingInputError` / `MdmaTypeError`:

```python
from mdma import get_inputs, validate_inputs

get_inputs(source)
# [InputDecl(name="project", type="string", has_default=False, default=None), ...]

validate_inputs(source, {"project": "Acme SDK", "version": "3.0.0", "date": "2026-07-01"})
# resolved inputs, with declared defaults applied
```

`parse_file(source)` is also exported for lower-level access to the parsed
template (inputs and blocks).

`render()` raises one of the exceptions in `mdma.errors` on failure:

| Exception | Condition |
|---|---|
| `MissingInputError` | a required input (no default) was not supplied |
| `MdmaTypeError` | an input's runtime type doesn't match its declared type, or a `<name:>` expression evaluates to something other than a string/number |
| `MdmaReferenceError` | a forward block reference, or an undefined variable |
| `FilterError` | a filter was applied to a value of the wrong type |
| `MdmaSyntaxError` | the `.mdma` source doesn't conform to the grammar (including `<name:>` used without a preceding `<multiple:>`) |
| `DuplicateNameError` | two items in a `<multiple:>` block computed the same `<name:>` value |

All are subclasses of `mdma.errors.MdmaError`.

## Behavioral notes not obvious from spec.md

- The blank line conventionally left between one block's content and the next
  block's header (or EOF) is treated as file formatting, not part of either
  block's rendered value — it's stripped from both ends of the block body
  before parsing. This is required for block references (`{{ blockname }}`)
  to be safely embeddable inline; otherwise every block value would carry a
  stray trailing newline from that separator. Blank lines *inside* a body are
  preserved exactly as written.
- Whitespace control (`{%-`/`-%}`) is applied per-tag, exactly as written —
  a conditional branch that renders empty does not retroactively remove
  surrounding blank-line text unless that text is trimmed by an adjacent `-`.
- Accessing a missing property on an `object`/`object[]` value (e.g.
  `entry.description` when `description` wasn't set) yields `None` rather
  than raising — objects are untyped maps, so this is normal and is what
  makes `| default(...)` useful on them. An undefined *root* identifier
  (typo'd variable/block/input name) still raises `MdmaReferenceError`.
- `default([])` and other array literals (`[a, b]`) are supported in
  expressions even though the formal grammar doesn't enumerate an
  array-literal production — the [filter reference](https://dastfox.github.io/mdma/filters/)
  relies on this syntax (`{{ list | default([]) }}`).
- `multiple` is a reserved word (can't be used as a block or input name), but
  `name` is not — `<name:>` is only ever recognized in its fixed position
  right after `<multiple:>`, so an input or block literally named `name`
  (e.g. `name: string`) is unaffected.

## Development

```bash
pip install -e ".[dev]"
pytest
```
