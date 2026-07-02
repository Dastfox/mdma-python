import pytest

from mdma import MdmaReferenceError, render_file, write_output


@pytest.fixture
def result(examples_dir):
    return render_file(
        examples_dir / "release-notes.mdma",
        {
            "project": "Acme SDK",
            "version": "3.0.0",
            "date": "2026-07-01",
            "releases": [
                {"version": "2.1.0", "date": "2026-06-01", "added": ["Dark mode"]},
                {"version": "2.0.0", "date": "2026-05-01", "added": ["Initial release"]},
            ],
        },
    )


def test_render_file_matches_render(examples_dir, result):
    source = (examples_dir / "release-notes.mdma").read_text()
    from mdma import render

    assert result == render(
        source,
        {
            "project": "Acme SDK",
            "version": "3.0.0",
            "date": "2026-07-01",
            "releases": [
                {"version": "2.1.0", "date": "2026-06-01", "added": ["Dark mode"]},
                {"version": "2.0.0", "date": "2026-05-01", "added": ["Initial release"]},
            ],
        },
    )


def test_write_output_all_blocks(tmp_path, result):
    written = write_output(result, tmp_path)

    assert (tmp_path / "slug.md").read_text() == result["slug"]
    assert (tmp_path / "title.md").read_text() == result["title"]
    assert (tmp_path / "release-notes.md").read_text() == result["release-notes"]
    assert (tmp_path / "changelog-entry" / "0.md").read_text() == result["changelog-entry"][0]
    assert (tmp_path / "changelog-entry" / "1.md").read_text() == result["changelog-entry"][1]
    assert len(written) == 5


def test_write_output_single_block(tmp_path, result):
    written = write_output(result, tmp_path, block="slug")

    assert written == [tmp_path / "slug.md"]
    assert (tmp_path / "slug.md").read_text() == result["slug"]
    assert not (tmp_path / "title.md").exists()


def test_write_output_named_multiple_block(tmp_path, examples_dir):
    named_result = render_file(
        examples_dir / "named-blocks.mdma",
        {
            "releases": [
                {"version": "2.1.0", "date": "2026-06-01", "added": ["Dark mode"]},
            ]
        },
    )

    write_output(named_result, tmp_path, block="changelog-by-version")

    assert (tmp_path / "changelog-by-version" / "2.1.0.md").read_text() == (
        named_result["changelog-by-version"]["2.1.0"]
    )


def test_write_output_unknown_block_raises(tmp_path, result):
    with pytest.raises(MdmaReferenceError):
        write_output(result, tmp_path, block="does-not-exist")


def test_write_output_rejects_path_traversal(tmp_path):
    malicious = {"changelog-by-version": {"../../evil": "pwned"}}

    with pytest.raises(ValueError):
        write_output(malicious, tmp_path, block="changelog-by-version")
