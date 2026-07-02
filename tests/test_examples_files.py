"""Render the repo's example .mdma files end to end as a smoke + golden test."""

from mdma import render


def test_simple_mdma(examples_dir):
    source = (examples_dir / "simple.mdma").read_text()
    result = render(
        source,
        {"name": "Widget", "description": "A small reusable widget.", "tags": ["ui", "core"]},
    )
    assert result["badge-line"] == "Widget — ui, core"
    assert result["body"] == "## Widget\n\nA small reusable widget.\n\n**Tags:** ui, core"


def test_simple_mdma_draft_and_no_tags(examples_dir):
    # `{% if tags | length > 0 -%}` has no leading `-`, so the blank line before it
    # is emitted even though the branch is false and renders empty (see the same
    # whitespace-control behavior verified in test_spec_example.py).
    source = (examples_dir / "simple.mdma").read_text()
    result = render(source, {"name": "Widget", "description": "Desc.", "draft": True})
    assert result["badge-line"] == "**[DRAFT]** Widget"
    assert result["body"] == "## Widget\n\nDesc.\n\n"


def test_release_notes_mdma_file(examples_dir):
    source = (examples_dir / "release-notes.mdma").read_text()
    result = render(
        source,
        {
            "project": "Acme SDK",
            "version": "3.0.0",
            "date": "2026-07-01",
            "added": ["WebSocket support"],
            "breaking": True,
            "releases": [
                {"version": "2.1.0", "date": "2026-06-01", "added": ["Dark mode"]},
            ],
        },
    )
    assert result["slug"] == "Acme SDK-3.0.0"
    assert result["title"] == "Acme SDK 3.0.0"
    assert isinstance(result["changelog-entry"], list)
    assert result["changelog-entry"][0] == "### 2.1.0 — 2026-06-01\n- Dark mode\n"


def test_named_blocks_mdma_file(examples_dir):
    source = (examples_dir / "named-blocks.mdma").read_text()
    result = render(
        source,
        {
            "releases": [
                {"version": "2.1.0", "date": "2026-06-01", "added": ["Dark mode"]},
                {"version": "2.0.0", "date": "2026-05-01", "added": ["Initial release"]},
            ],
        },
    )
    assert result["changelog-by-version"] == {
        "2.1.0": "### 2.1.0 — 2026-06-01\n- Dark mode\n",
        "2.0.0": "### 2.0.0 — 2026-05-01\n- Initial release\n",
    }
