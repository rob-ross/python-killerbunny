#  File: normalizer.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

"""Methods dealing with normalizing JPath expressions."""

import json
import os
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import cast, Callable

from common.screen_utils import display_list_elements
from killerbunny.shared.json_type_defs import JSON_ValueType, JSON_PRIMITIVE_TYPES, JSON_ARRAY_TYPES, \
    JSON_OBJECT_TYPES
from killerbunny.lexing.lexer import JPathLexer
from killerbunny.incubator.jsonpointer.constants import SCALAR_TYPES, PATH_VALUE_SEPARATOR, ONE_MEBIBYTE, JPATH_VALUES_SUFFIX
from killerbunny.shared.jpath_bnf import JPathBNFConstants
from killerbunny.incubator.jsonpointer.pretty_printer import FormatFlags, format_scalar, pretty_print



@dataclass
class PathValueNode:
    path: str
    value: JSON_ValueType
    

def label_all_nodes_normal_form_breadth_first(
                                        json_value: JSON_ValueType,
                                        element_list: list[str],
                                        format_: FormatFlags,
                                        root_path: str = "",
                                        level: int = 0,
                                        ) -> list[str]:
    """Similer to label_all_nodes_normal_form, but breadth-first traversal.
    Breadth-first
     start: put root element in queue.
     - each iteration
    1. pull next element from top of queue and process it.
    2. add all child elements of current element to end queue.
    
    """

        
    deq:deque[PathValueNode] = deque()
    deq.append(PathValueNode(JPathBNFConstants.ROOT_IDENTIFIER, json_value))
    
    current_node: PathValueNode
    while len(deq) > 0:
        current_node = deq.popleft()
        value = current_node.value
        path = current_node.path
        if isinstance(value, JSON_PRIMITIVE_TYPES):
            # these are terminals, so add path and  value. No children
            element_list.append(
                f'{path}{PATH_VALUE_SEPARATOR}{format_scalar(value, format_)}\n')
        elif isinstance(value, JSON_ARRAY_TYPES):
            element_list.append(f'{path}{PATH_VALUE_SEPARATOR}{pretty_print(value, format_, [])}\n')
            # push children on the deque
            for i, item in enumerate(value):
                deq.append( PathValueNode(f"{path}[{i}]", item) )
        elif isinstance(value, JSON_OBJECT_TYPES):
            element_list.append(
                f'{path}{PATH_VALUE_SEPARATOR}{pretty_print(value, format_, [])}\n')
            for k, v in value.items():
                deq.append( PathValueNode(f"{path}['{k}']", v) )
        else:
            raise ValueError(f"Unexpected type: {type(current_node)}")
    
    return element_list


def label_all_nodes_normal_form_depth_first(json_value: JSON_ValueType,
                                            element_list: list[str],
                                            format_: FormatFlags,
                                            root_path: str = "",
                                            level: int = 0,
                                            ) -> list[str]:
    """Recursive depth-first traversal of json value in argument, create a normalized JSON Path path for each element and return all paths
    as  str : str pairs, separated by _SEPARATOR..
    Left str is the normalized JSON Path, right str is the serialzed JSON value to which that path refers.
    """
    if isinstance(json_value, SCALAR_TYPES):
        # these are terminals, so add path and  value
        element_list.append(
            f'{root_path}{PATH_VALUE_SEPARATOR}{format_scalar(json_value, format_)}\n')
    elif isinstance(json_value, list):
        path = JPathBNFConstants.ROOT_IDENTIFIER if not root_path and level == 0 else root_path
        # path = root_path
        element_list.append(f'{path}{PATH_VALUE_SEPARATOR}{pretty_print(json_value, format_, [])}\n')
        path = root_path
        for i, item in enumerate(json_value):
            label_all_nodes_normal_form_depth_first(item, element_list, format_, f"{path}[{i}]", level + 1)
    elif isinstance(json_value, dict):
        path = root_path if root_path else JPathBNFConstants.ROOT_IDENTIFIER
        element_list.append(
            f'{path}{PATH_VALUE_SEPARATOR}{pretty_print(json_value, format_, [])}\n')
        for key, value in json_value.items():
            label_all_nodes_normal_form_depth_first(value, element_list, format_, f"{path}['{key}']", level + 1)
 
    return element_list


def add_shorthand_notation(lines: list[str]) -> list[str]:
    """Given the ouput from label_all_nodes_normal_form_xxx, add a line for any line with a bracket child reference
    converted to using member-name-shorthand notation.
    E.g., given a line like:
        $['store']['bicycle']
    returns the list
        $['store']['bicycle']
        $.store.bicycle
    
    Not all name selectors (["foo"]) can be converted to shorthand notation. Only those that match the regex pattern
    JPathBNFConstants.NAME_SELECTOR_PATTERN will be converted
    """
    grammar = JPathBNFConstants()
    result: list[str] = []
    name_re = re.compile(fr"\[['\"]({grammar.MEMBER_NAME_SHORTHAND})['\"]]")
    for index, line in enumerate(lines):
        line = line.split(PATH_VALUE_SEPARATOR)[0].rstrip()  # discard the json value part
        result.append(line)
        line_subs:str = line
        matches = name_re.findall(line)
        for match in matches:
            search_str = f"['{match}']"
            result.append(f"{line.replace(search_str, f'.{match}')}")
            line_subs = line_subs.replace(search_str, f'.{match}')
        if index > 0 and line_subs != result[-1]:  # avoid duplicate substitutions
            result.append(line_subs)  # full substitution of all name selectors
    return result

def add_double_quoted_versions(lines: list[str]) -> list[str]:
    """ For every line in the input, add a duplicate line with all the single quotes reqplaced by double quotes
    This method is naive and will not work for quote characters in string literals. Examine using regex substitution
    if that becomes a problem.
    """
    result: list[str] = []
    for line in lines:
        result.append(line)
        new_line = line.replace("'", '"')
        if result[-1] != new_line:
            result.append(new_line)  # avoid duplicate substitutions
    return result

def lexcercise(lines: list[str]) -> list[str]:
    """Given an input list of valid, well formed Json path identifiers, run each linethrough lexer
    to generate a token list and  append these to each line, separated by PATH_SEPARATOR. This creates a testing file."""
    result: list[str] = []
    for line in lines:
        tokens = JPathLexer("",line).tokenize()[0]
        rmap = map(lambda x: x.__testrepr__(), tokens)
        result.append(f"{line}{PATH_VALUE_SEPARATOR}{pretty_print(list(rmap),FormatFlags(), [],0)}")
    return result

def load_obj_from_json_file(input_file: Path) -> JSON_ValueType:
    """Return the  json object from the json file in the argument.
    Intended for a json file with a single object for testing and debugging. """
    with open(input_file, "rb", buffering=ONE_MEBIBYTE) as in_file:
        json_str = in_file.read()
        return cast(JSON_ValueType, json.loads(json_str))


def generate_test_parameters(
        json_file_path: Path,
        save_test_file: bool = False,
        func: Callable[ [JSON_ValueType, list[str], FormatFlags, str, int], list[str]] = label_all_nodes_normal_form_depth_first
) -> str:
    
    """ Generate test parameters for testing a json object with JSON Pointers. Return parameters
    as a str. If save_test_file is True, also create and save a path_values test file for the
    json file in the same directory
    """
    jobj = load_obj_from_json_file(json_file_path)
    result: list[str] = func( jobj, [], FormatFlags().as_json_format().with_single_line(True), "", 0)
    s = ''.join(result)
    print(s)
    if save_test_file:
        test_file = json_file_path.with_name(f"{json_file_path.stem}{JPATH_VALUES_SUFFIX}")
        with open(test_file, "w", encoding="utf-8", buffering=ONE_MEBIBYTE) as out_file:
            out_file.write(s)
        # _logger.info(f"Created {test_file}")
        print(f"Created {test_file}")
    return s

def subpath(paths: list[str], path_component_index:int = -1) -> str:
    """Return the subpath composed of first N reference tokens, where N == path_component_index argument.
    If path_component_index == -1. return the full path.
    """
    subpath = "$"
    start = 0
    end = len(paths) if path_component_index == -1 else path_component_index + 1
    for index in range(start, end):
        if paths[index].isdigit():
            subpath += f"[{paths[index]}]"
        elif paths[index] == "$":
            continue
        else:
            subpath += f"['{paths[index]}']"
    return subpath

def resolve_json_path(json_value: JSON_ValueType, normalized_jpath: str) -> tuple[PathValueNode, str | None] :
    """Path must be normalized and single query result"""
    if normalized_jpath == JPathBNFConstants.ROOT_IDENTIFIER:
        return PathValueNode(JPathBNFConstants.ROOT_IDENTIFIER, json_value), None
    
    segment_parts_re = r"\['?([0-9]+|[\w\s]+?)'?\]"
    segment_parts = ['$'] + re.findall(segment_parts_re, normalized_jpath)
    print(f"normalized_jpath = {normalized_jpath}")
    print(f"results = {segment_parts}")
    
    cur_node = json_value
    last_path_index = len(segment_parts) - 1
    for index, segment_part in enumerate(segment_parts):
        if index == 0 and segment_part == JPathBNFConstants.ROOT_IDENTIFIER:
            continue  # first token in list of len > 1, this is just the root identifier, so skip
        if isinstance(cur_node, JSON_OBJECT_TYPES):
            if segment_part not in cur_node:
                raise KeyError(f"Invalid dict key: '{segment_part}' in path '{subpath(segment_parts, index)}'")
            cur_node = cur_node[segment_part]
        elif isinstance(cur_node, JSON_ARRAY_TYPES):
            list_length = len(cur_node)
            try:
                i = int(segment_part)
                if  i >= list_length or i < 0:
                    raise IndexError(f"Invalid list index {i} in path "
                                     f"'{subpath(segment_parts,index)}' for list of length {list_length}")
                cur_node = cur_node[int(segment_part)]
            except ValueError:
                # raise ... from None prevents chaining the ValueError from the int(unsec_path), which we are handling here
                raise ValueError(f"Invalid list index type:{type(segment_part).__name__} in path "
                                 f"'{subpath(segment_parts,index)}'") from None
        elif isinstance(cur_node, SCALAR_TYPES):
            # terminal node, should align with end of path
            # todo error handling if more path components left to process
            if index != last_path_index:
                raise ValueError(f"Invalid path reference '{subpath(segment_parts,index+1)}', last good value: '{cur_node}' for path '{subpath(segment_parts,index)}'")
        else:
            raise TypeError(f"Encountered non JSON type: {type(cur_node)}")
        
        if isinstance(cur_node, SCALAR_TYPES) and index != last_path_index:
            #print(f"*********** TERMINAL NODE REACHED, BUT PATH CONTINUES *****")
            raise ValueError(f"Invalid path reference '{subpath(segment_parts,index+1)}', last good value: '{cur_node}' "
                             f"for path '{subpath(segment_parts,index)}'")
        
    return PathValueNode(normalized_jpath, cur_node), None

def t_resolve() -> None:
    file3 = Path(FRAGILE_TEST_DIR) / "jpath_files/bookstore.json"
    jobj = load_obj_from_json_file(file3)
    path_value, error = resolve_json_path(jobj, "$['store']['book'][3]['price']")
    print(f"path_value = {path_value}")
    
    path_value, error = resolve_json_path(jobj, "$['store']['book'][3]['isbn']")
    print(f"path_value = {path_value}")
    
    # invalid key
    try:
        path_value, error = resolve_json_path(jobj, "$['store']['book'][3]['no key']")
        print(f"path_value = {path_value}")
    except KeyError as e:
        print(f"error = {e}")
    
    # invalid array index
    try:
        path_value, error = resolve_json_path(jobj, "$['store']['book'][4]['isbn']")
        print(f"path_value = {path_value}")
    except IndexError as e:
        print(f"error = {e}")

FRAGILE_TEST_DIR = '/test_jpath_interpreter'

def t_1() -> None:
    file1 = Path(FRAGILE_TEST_DIR) / "jpath_files/json.1.json"
    file2 = Path(FRAGILE_TEST_DIR) / "jpath_files/daffydowndilly.json"
    file3 = Path(FRAGILE_TEST_DIR) / "jpath_files/bookstore.json"
    generate_test_parameters(file3, False, func= label_all_nodes_normal_form_breadth_first )
    
    print()
    t_resolve()
    
def t_2() -> None:
    file1 = Path(FRAGILE_TEST_DIR) / "incubator/jpath/rfc9535_examples/figure.1.json"
    #generate_test_parameters(file1, False, func= label_all_nodes_normal_form_depth_first )
    
    json_value = load_obj_from_json_file(file1)
    lines = label_all_nodes_normal_form_depth_first(json_value, [], FormatFlags().as_json_format().with_single_line(True), "", 0)
    lines = add_shorthand_notation(lines)
    display_list_elements(lines,single_line=False, quote=False)
    lines = add_double_quoted_versions(lines)
    print()
    lines = lexcercise(lines)
    display_list_elements(lines,single_line=False, quote=False)

def main() -> None:
    print(os.getcwd())
    t_2()

    
if __name__ == '__main__':
    main()