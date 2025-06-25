# Inside: packages/killerbunny/tests/conftest.py
from typing import Callable, Any

import pytest
from pathlib import Path
import json  # Assuming load_obj_from_json_file needs json


# Define the fixture for the directory path
@pytest.fixture(scope="session")  # Calculate once per session
def json_files_dir_fixture() -> Path:
    """Provides the Path to the test JSON files directory."""
    # __file__ is .../tests/conftest.py
    # .parent gives .../tests/
    test_root_dir = Path(__file__).parent / "incubator/jsonpointer"
    # Construct path relative to conftest.py
    path = test_root_dir / "json_files"
    if not path.is_dir():
        raise FileNotFoundError(f"Test JSON files directory not found at {path}")
    return path


# Optional: Make loading a fixture too
@pytest.fixture(scope="session")
def load_obj_from_json_file_func() -> Callable[[Path], dict[str, Any]]:
    """Provides the loading function as a fixture."""

    def _loader(file_path: Path) -> Any:
        if not file_path.is_file():
            raise FileNotFoundError(f"Cannot load JSON from non-existent file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    return _loader

# You could also put find_json_test_file_stems etc. here if they
# are purely test utilities, perhaps wrapped in fixtures.
