"""Golden-output test using the worked example from spec.md section 8."""

from mdma import parse_file, render, render_template

TEMPLATE = """\
@inputs
project:  string
version:  string
date:     string
added:    string[] = []
changed:  string[] = []
fixed:    string[] = []
breaking: boolean  = false
releases: object[] = []

<slug>
{{ project }}-{{ version }}

<title>
{{ project }} {{ version }}

<release-notes>
# {{ title }} — {{ date }}

{%- if breaking %}

> **Breaking changes included in this release.**
{%- endif %}

{% if added | length > 0 -%}
### Added
{% for item in added -%}
- {{ item }}
{% endfor -%}
{% endif %}

{% if changed | length > 0 -%}
### Changed
{% for item in changed -%}
- {{ item }}
{% endfor -%}
{% endif %}

{% if fixed | length > 0 -%}
### Fixed
{% for item in fixed -%}
- {{ item }}
{% endfor -%}
{% endif %}

<changelog-entry
multiple: entry in releases
>

### {{ entry.version }} — {{ entry.date }}
{% for item in entry.added -%}
- {{ item }}
{% endfor %}
"""

INPUTS = {
    "project": "Acme SDK",
    "version": "3.0.0",
    "date": "2026-07-01",
    "added": ["WebSocket support"],
    "breaking": True,
    "releases": [
        {"version": "2.1.0", "date": "2026-06-01", "added": ["Dark mode"]},
        {"version": "2.0.0", "date": "2026-05-01", "added": ["Initial release"]},
    ],
}


def test_slug():
    result = render(TEMPLATE, INPUTS)
    assert result["slug"] == "Acme SDK-3.0.0"


def test_title():
    result = render(TEMPLATE, INPUTS)
    assert result["title"] == "Acme SDK 3.0.0"


def test_release_notes():
    # Note: this differs from the abbreviated "Produces" table in spec.md section 8.
    # The added/changed/fixed sections use `{% if ... -%}` (trim only after the tag),
    # unlike `breaking`'s `{%- if %}...{%- endif %}` (trim both sides). Since changed
    # and fixed are both empty here, their `{% if %}`/`{% endif %}` tags render to "",
    # but the blank-line text surrounding them is untouched by whitespace control (no
    # leading `-`) and is therefore emitted literally -- per the documented per-tag
    # trim rules in spec.md section 5.3.
    result = render(TEMPLATE, INPUTS)
    expected = (
        "# Acme SDK 3.0.0 — 2026-07-01\n"
        "\n"
        "> **Breaking changes included in this release.**\n"
        "\n"
        "### Added\n"
        "- WebSocket support\n"
        "\n"
        "\n"
        "\n"
        "\n"
    )
    assert result["release-notes"] == expected


def test_changelog_entry_is_array_of_two():
    result = render(TEMPLATE, INPUTS)
    entries = result["changelog-entry"]
    assert isinstance(entries, list)
    assert len(entries) == 2
    assert entries[0] == "### 2.1.0 — 2026-06-01\n- Dark mode\n"
    assert entries[1] == "### 2.0.0 — 2026-05-01\n- Initial release\n"


def test_render_template_on_pre_parsed_template_matches_render():
    assert render_template(parse_file(TEMPLATE), INPUTS) == render(TEMPLATE, INPUTS)
