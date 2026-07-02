from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES_DIR
