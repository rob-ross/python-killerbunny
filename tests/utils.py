"""Utility functions to support testing"""
#  File: utils.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
import json
import logging
from pathlib import Path
from typing import Any, NamedTuple, cast

from killerbunny.incubator.jsonpointer.constants import ONE_MEBIBYTE, UTF8, PATH_VALUE_SEPARATOR, ROOT_PATH_DISPLAY_STR, EMPTY_STRING, \
    SCALAR_TYPES, PATH_VALUES_SUFFIX, JSON_FILE_SUFFIX, JSON_VALUES
from killerbunny.incubator.jsonpointer.json_pointer import escape_ref_token
from killerbunny.incubator.jsonpointer.pretty_printer import pretty_print, FormatFlags, format_scalar

TEST_DIR = Path(__file__).parent
JSON_FILES_DIR = TEST_DIR / "incubator/jsonpointer/json_files"

_logger = logging.getLogger(__name__)


def load_obj_from_json_file(input_file: Path) -> JSON_VALUES:
    """Return the  json object from the json file in the argument.
    Intended for a json file with a single object for testing and debugging. """
    with open(input_file, "rb", buffering=ONE_MEBIBYTE) as in_file:
        json_str = in_file.read()
        return cast(JSON_VALUES, json.loads(json_str))


class PathValues(NamedTuple):
    path: str
    # value is stored in file as a string, but it's a serialized JSON object, and will be deserialized into Python objects
    # during testing
    value: Any

def label_all_nodes(obj: JSON_VALUES,
                    element_list: list[Any],
                    format_: FormatFlags,
                    root_path: str = "",
                    level: int = 0,
                    ) -> Any:
    """Depth first traversal of json object in argument, create a JSON Pointer path for each element and return all paths
    as a str"""
    if isinstance(obj, SCALAR_TYPES):
        # these are terminals, so add path and  value
        element_list.append(
            f'{root_path}{PATH_VALUE_SEPARATOR}{format_scalar(obj, format_)}\n')
    elif isinstance(obj, list):
        path = ROOT_PATH_DISPLAY_STR if not root_path and level == 0 else root_path
        # path = root_path
        element_list.append(f'{path}{PATH_VALUE_SEPARATOR}{pretty_print(obj, format_, [])}\n')
        path = root_path
        for i, item in enumerate(obj):
            label_all_nodes(item, element_list, format_,f"{path}/{i}", level + 1)
        element_list.append(f'{path}/-{PATH_VALUE_SEPARATOR}{len(obj)}\n')
    elif isinstance(obj, dict):
        path = root_path if root_path else ROOT_PATH_DISPLAY_STR
        element_list.append(
            f'{path}{PATH_VALUE_SEPARATOR}{pretty_print(obj, format_, [])}\n')
        for key, value in obj.items():
            label_all_nodes(value, element_list, format_, f"{root_path}/{escape_ref_token(key)}", level + 1)
    if level == 0:
        return ''.join(element_list)  # final invocation of this method, exiting to original caller
    return element_list




def load_path_values(path_values_path: Path) -> list[PathValues]:
    """Load parameter data for testing JSON Pointer paths against a json dict test harness"""
    values: list[PathValues] = []
    with open(path_values_path, "r", encoding=UTF8, buffering=ONE_MEBIBYTE) as in_file:
        for line in in_file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            lines: list[str] = line.split(PATH_VALUE_SEPARATOR)
            p = lines[0]
            if p == ROOT_PATH_DISPLAY_STR:
                p = EMPTY_STRING
            v = json.loads(lines[1])
            pv = PathValues(p, v)
            values.append(pv)
    return values


def generate_test_parameters(json_file_path: Path, save_test_file: bool = False) -> str:
    """ Generate test parameters for testing a json object with JSON Pointers. Return parameters
    as a str. If save_test_file is True, also create and save a path_values test file for the
    json file in the same directory
    """
    jobj = load_obj_from_json_file(json_file_path)
    s: str = label_all_nodes(jobj, [], FormatFlags().as_json_format().with_single_line(True))
    print(s)
    if save_test_file:
        test_file = json_file_path.with_name(f"{json_file_path.stem}{PATH_VALUES_SUFFIX}")
        with open(test_file, "w", encoding="utf-8", buffering=ONE_MEBIBYTE) as out_file:
            out_file.write(s)
        # _logger.info(f"Created {test_file}")
        print(f"Created {test_file}")
    return s


def _find_json_test_file_stems_impl(file_stems: list[str], root_search_path: Path) -> list[str]:
    """Search recursively starting in the root_searh_path for any files ending in '.json' and append the file
    stems to the file_stems list argument and return this same list.
    """
    file_path: Path
    for file_path in root_search_path.iterdir():
        # print(f"{file_path}, {file_path.suffix=}, {file_path.suffix == _JSON_FILE_SUFFIX}")
        if file_path.is_dir():  # recursively check subdirectories
            _find_json_test_file_stems_impl(file_stems, file_path)
        elif file_path.suffix == JSON_FILE_SUFFIX:
            file_stems.append(file_path.stem)
    return file_stems

def find_json_test_file_stems(root_search_path: Path) -> list[str]:
    """Search recursively starting in the root_searh_path for any files ending in '.json' return the stems for each
     """
    return _find_json_test_file_stems_impl([], root_search_path)



def find_json_test_file(file_name: str, root_search_path: Path) -> Path | None:
    """Search recursively for the file named file_name, starting in the root_search_path"""
    file_path: Path
    for file_path in root_search_path.iterdir():
        if (not file_path.is_dir()) and file_path.name == file_name:
            return file_path
    for file_path in root_search_path.iterdir():
        if file_path.is_dir():  # recursively check subdirectories
            return find_json_test_file(file_name, file_path)
    return None

def print_list(list_: list[Any]) -> None:
    for item in list_:
        print(item)




def main() -> None:
    ...
    #   \U0001f600 start of emoji pages
    # start_code_point = 0x1F600
    # end_code_point = 0x1F64F
    # for code_point in range(start_code_point, end_code_point + 1):
    #     print(chr(code_point))


if __name__ == '__main__':
    main()
