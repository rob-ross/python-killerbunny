# type: ignore
from pathlib import Path
from typing import Any

import pytest

from killerbunny.incubator.jsonpointer.constants import PATH_VALUES_SUFFIX, JSON_FILE_SUFFIX
from killerbunny.incubator.jsonpointer.json_pointer import resolve_json_pointer, \
    unescape_ref_token, escape_ref_token, validate

from utils import find_json_test_file_stems, find_json_test_file, \
    load_obj_from_json_file, load_path_values, JSON_FILES_DIR


def path_values_data(json_files_dir_fixture:Path = JSON_FILES_DIR):
    """Generate parameter data for test_resolve_json_pointer() parameterized test

    Loads path:values data from a .path_values.txt file.
    To add a new json file for testing, create the json file in _JSON_FILES_DIR (or nested dir)
    and call generate_test_parameters() with the file Path for the new file. It will
    create a .path_values.txt file with the same stem as the json file. Add the stem
    to the file_stems array.
     """

    file_stems = find_json_test_file_stems(json_files_dir_fixture)  # load dynamically from test dir

    all_test_cases = []  # Collect all data here
    for file_stem in file_stems:
        json_obj_path = find_json_test_file(f"{file_stem}{JSON_FILE_SUFFIX}", json_files_dir_fixture)
        if json_obj_path is None or not json_obj_path.exists():
            raise FileNotFoundError(f"Test harness file not found: {file_stem}{JSON_FILE_SUFFIX}")
        test_parameters_path = find_json_test_file(f"{file_stem}{PATH_VALUES_SUFFIX}", json_files_dir_fixture)
        if not test_parameters_path.exists():
            raise FileNotFoundError(f"Test parameters file not found: {file_stem}{PATH_VALUES_SUFFIX}")

        # print(f"Loading value from: {json_obj_path}")
        # print(f"Loading parameter data from: {test_parameters_path}")
        json_obj  = load_obj_from_json_file(json_obj_path)
        parameter_data = load_path_values(test_parameters_path)
        for path, expected_value in parameter_data:
            all_test_cases.append((file_stem, json_obj, path, expected_value))
    return all_test_cases



@pytest.mark.parametrize("filename, value, path, expected_value", path_values_data())
def test_resolve_json_pointer(filename, value, path, expected_value):
    """Test resolve_json_pointer() with data from .path_values.txt files."""
    #print(f"\ntest_resolve_json_pointer called for file: {filename}, path: {path}")

    actual_value = resolve_json_pointer(value, path)
    assert actual_value == expected_value, f"{actual_value=}\n{expected_value=}"


@pytest.fixture(scope="module")
def json_object_fixture(json_files_dir_fixture: Path, load_obj_from_json_file_func) -> dict:
    jobj_path = json_files_dir_fixture / "json.1.json"
    jobj = load_obj_from_json_file_func(jobj_path)
    return jobj


bad_path_values_data = [
     ("/name/0", ValueError, "Invalid path reference '/name/0', last good value: 'John Doe' for path '/name'"),
     ("/name/foo", ValueError, "Invalid path reference '/name/foo', last good value: 'John Doe' for path '/name'"),
     ("/phoneNumbers/foo", IndexError, "Invalid list index format 'foo' in path '/phoneNumbers/foo'"),
     ("/phoneNumbers/-1", IndexError, "Invalid list index format '-1' in path '/phoneNumbers/-1'"),
     ("/phoneNumbers/37", IndexError, "Invalid list index 37 in path '/phoneNumbers/37' for list of length 2"),
     ("/foo", KeyError, "Invalid dict key 'foo' in path '/foo'"),
     ("/phoneNumbers/1/foo", ValueError, "Invalid path reference '/phoneNumbers/1/foo', last good value: '555-987-6543' for path '/phoneNumbers/1'"),
     ("/address/city/1", ValueError, "Invalid path reference '/address/city/1', last good value: 'Anytown' for path '/address/city'"),
     ("/address/city/foo", ValueError, "Invalid path reference '/address/city/foo', last good value: 'Anytown' for path '/address/city'"),

]
@pytest.mark.parametrize("path, expected_exception_type, expected_exception_message", bad_path_values_data)
def test_resolve_bad_paths(path, expected_exception_type, expected_exception_message, json_object_fixture) -> None:
    """Test resolve_json_pointer() with bad path test cases that raise exceptions against json.1.json file """
    with pytest.raises(expected_exception_type) as exc_info:
        resolve_json_pointer(json_object_fixture, path)
    assert expected_exception_message in str(exc_info.value)


@pytest.mark.parametrize("filename, value, path, expected_value", path_values_data())
def test_validate(filename, value, path, expected_value) -> None:
    assert validate(value, path) == True


@pytest.mark.parametrize("path, expected_exception_type, expected_exception_message", bad_path_values_data)
def test_validate_bad_paths(path, expected_exception_type, expected_exception_message, json_object_fixture) -> None:
    assert validate(json_object_fixture, path) == False

unescape_tests = [("~01", "~1"),
                  ("~10", "/0"),
                  ("m~0n", "m~n")
]
@pytest.mark.parametrize("escaped_ref_token, expected", unescape_tests)
def test_unescape(escaped_ref_token: str, expected: str) -> None:
    actual = unescape_ref_token(escaped_ref_token)
    assert actual == expected


escape_tests = [("~1", "~01"),
                ("/0","~10"),
                ("m~n", "m~0n" ),
]
@pytest.mark.parametrize("unescaped_ref_token, expected", escape_tests)
def test_escape(unescaped_ref_token: str, expected: str) -> None:
    actual = escape_ref_token(unescaped_ref_token)
    assert actual == expected