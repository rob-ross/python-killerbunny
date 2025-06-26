#  File: test_root_value_cycles.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

"""Tests the evaluator with cyclic data. Cycles cannot be (easily?) represented in JSON text but could easily happen
when generating nested data programmatically. Cycles can be used as an attack vector to crash the evaluator with
a stack overflow error. """
from typing import Any

import pytest
from _pytest.logging import LogCaptureFixture

from killerbunny.evaluating.value_nodes import VNodeList
from killerbunny.evaluating.well_formed_query import WellFormedValidQuery
from killerbunny.shared.json_type_defs import JSON_ValueType

@pytest.fixture(scope="module", autouse=True)
def child_dict_cycle() -> JSON_ValueType:
    parent_dict: dict[str, JSON_ValueType] = { "one": 1 }
    dict_cycle = parent_dict
    parent_dict["cycle"] = dict_cycle
    return parent_dict

@pytest.fixture(scope="module", autouse=True)
def grandchild_dict_cycle() -> JSON_ValueType:
    nested_dict: dict[str, JSON_ValueType] = { "apple": "a", "banana": "b", "orange": "o" }
    parent_dict: dict[str, JSON_ValueType] = { "one": 1, "two": 2 , "nested":nested_dict }
    dict_cycle = parent_dict
    nested_dict["cycle"] = dict_cycle
    return parent_dict

@pytest.fixture(scope="module", autouse=True)
def child_list_cycle() -> JSON_ValueType:
    parent_list: list[Any] = [1]
    list_cycle = parent_list
    parent_list.append(list_cycle)
    return parent_list

@pytest.fixture(scope="module", autouse=True)
def grandchild_list_cycle() -> JSON_ValueType:
    """a list with a cycle in an element list"""
    nested_list: list[Any] = [ 1, 2, 3]
    parent_list: list[Any] = [ "one", "two", nested_list]  # nested_list will contain the parent list as an element
    list_cycle = parent_list
    nested_list.append(list_cycle)
    return parent_list

def log_msg_assert(msg: str, caplog: LogCaptureFixture) -> None:
    """Helper method to ensure the logging message in `msg` was logged as expected."""
    assert len(caplog.records) > 0
    record = caplog.records[0]
    msgs = [record.msg for record in caplog.records]
    assert record.levelname == "WARNING"
    assert msg in msgs


def test_cs_dict(child_dict_cycle: JSON_ValueType, caplog: LogCaptureFixture) -> None:
    jpath_query_str = '$[*]'
    query = WellFormedValidQuery.from_str(jpath_query_str)
    
    node_list:VNodeList = query.eval(child_dict_cycle)
    expected_values = [1]  # eval will not include a cycle in the result, so the cyclic parent_dict is not included
    
    actual_values = list(node_list.values())
    assert len(actual_values) == len(expected_values)
    assert actual_values[0]   == expected_values[0]
    
    actual_paths = [npath.jpath_str for npath in node_list.paths() ]
    assert actual_paths == ["$['one']"]
    
    log_msg_assert(
        "Circular reference cycle detected: current node: $['cycle'], {'one': 1, 'cycle': {...}} already included as: $, {'one': 1, 'cycle': {...}}",
        caplog
    )

# noinspection SpellCheckingInspection
def test_ds_dict(child_dict_cycle: JSON_ValueType, caplog: LogCaptureFixture)-> None:
    jpath_query_str = '$..[*]'
    query = WellFormedValidQuery.from_str(jpath_query_str)
    
    node_list:VNodeList = query.eval(child_dict_cycle)
    
    expected_values = [1]  # eval will not include a cycle in the result, so the cyclic parent_dict is not included
    
    actual_values = list(node_list.values())
    print(f"\nactual_values = {actual_values}")
    assert len(actual_values) == len(expected_values)
    assert actual_values[0]   == expected_values[0]
    
    actual_paths = [npath.jpath_str for npath in node_list.paths() ]
    assert actual_paths == ["$['one']"]
    
    log_msg_assert(
        "Circular reference cycle detected: current node: $['cycle'], {'one': 1, 'cycle': {...}} already included as: $, {'one': 1, 'cycle': {...}}",
        caplog
    )

def test_cs_dict_grandchild(grandchild_dict_cycle: JSON_ValueType, caplog: LogCaptureFixture) -> None:
    jpath_query_str = '$[*]'
    query = WellFormedValidQuery.from_str(jpath_query_str)
    
    node_list:VNodeList = query.eval(grandchild_dict_cycle)
    expected_values = [1, 2, { "apple": "a", "banana": "b", "orange": "o", "cycle": grandchild_dict_cycle}]
    
    actual_values = list(node_list.values())
    assert len(actual_values) == len(expected_values)
    assert actual_values[0] == expected_values[0]
    assert actual_values[1] == expected_values[1]
    assert actual_values[2] == expected_values[2]
    
    actual_paths = [npath.jpath_str for npath in node_list.paths() ]
    assert actual_paths == ["$['one']", "$['two']", "$['nested']"]

def test_ds_dict_grandchild(grandchild_dict_cycle: JSON_ValueType, caplog: LogCaptureFixture) -> None:
    jpath_query_str = '$..[*]'
    query = WellFormedValidQuery.from_str(jpath_query_str)
    
    node_list:VNodeList = query.eval(grandchild_dict_cycle)
    expected_values = [1, 2, { "apple": "a", "banana": "b", "orange": "o", "cycle": grandchild_dict_cycle}, 'a', 'b', 'o']
    
    actual_values = list(node_list.values())
    assert len(actual_values) == len(expected_values)
    assert actual_values[0] == expected_values[0]
    assert actual_values[1] == expected_values[1]
    assert actual_values[2] == expected_values[2]
    assert actual_values[3] == expected_values[3]
    assert actual_values[4] == expected_values[4]
    assert actual_values[5] == expected_values[5]
    
    actual_paths = [npath.jpath_str for npath in node_list.paths() ]
    expected_paths = ["$['one']",
                      "$['two']",
                      "$['nested']",
                      "$['nested']['apple']",
                      "$['nested']['banana']",
                      "$['nested']['orange']"]
    assert actual_paths == expected_paths
    
    log_msg_assert(
        "Circular reference cycle detected: current node: $['nested']['cycle'], "
         "{'one': 1, 'two': 2, 'nested': {'apple': 'a', 'banana': 'b', 'orange': 'o', "
         "'cycle': {...}}} already included as: $, {'one': 1, 'two': 2, 'nested': "
         "{'apple': 'a', 'banana': 'b', 'orange': 'o', 'cycle': {...}}}",
        caplog
    )
    
def test_cs_list_grandchild(grandchild_list_cycle: JSON_ValueType, caplog: LogCaptureFixture) -> None:
    """There is a cycle from the parent list to its last element, which is a list that includes
    the parent list as a member.
    This query will not cause infinite recursion because it only processes the children of the parent"""
    jpath_query_str = '$[*]'
    query = WellFormedValidQuery.from_str(jpath_query_str)
    
    node_list:VNodeList = query.eval(grandchild_list_cycle)
    # eval will not include a cycle in the result, so the cyclic parent_list is not included in the nested list
    expected_values = ["one", "two", [1,2,3, grandchild_list_cycle]]
    
    actual_values = list(node_list.values())
    assert len(actual_values) == len(expected_values)
    actual_values_str = f"{actual_values}"
    expected_values_str = f"['one', 'two', [1, 2, 3, ['one', 'two', [...]]]]"
    assert actual_values_str == expected_values_str
    
    assert actual_values[0] == expected_values[0]
    assert actual_values[1] == expected_values[1]
    assert actual_values[2] == expected_values[2]
    
    actual_paths = [npath.jpath_str for npath in node_list.paths() ]
    assert actual_paths == ['$[0]', '$[1]', '$[2]']

def test_ds_list_grandchild(grandchild_list_cycle: JSON_ValueType, caplog: LogCaptureFixture) -> None:
    """There is a cycle from the parent list to its last element, which is a list that includes
    the parent list as a member.Cyclic parent is not included in as a result node.
    """
    jpath_query_str = '$..[*]'
    query = WellFormedValidQuery.from_str(jpath_query_str)
    
    node_list:VNodeList = query.eval(grandchild_list_cycle)
    # eval will not include a cycle in the result, so the cyclic parent_list is not included in the nested list
    expected_values = ["one", "two", [1,2,3, grandchild_list_cycle], 1, 2, 3]
    
    actual_values = list(node_list.values())
    actual_values_str = f"{actual_values}"
    expected_values_str = f"['one', 'two', [1, 2, 3, ['one', 'two', [...]]], 1, 2, 3]"
    
    assert actual_values_str == expected_values_str
    
    assert len(actual_values) == len(expected_values)
    assert actual_values[0] == expected_values[0]
    assert actual_values[1] == expected_values[1]
    assert actual_values[2] == expected_values[2]
    assert actual_values[3] == expected_values[3]
    assert actual_values[4] == expected_values[4]
    assert actual_values[5] == expected_values[5]
    
    actual_paths = [npath.jpath_str for npath in node_list.paths() ]
    expected_paths = ['$[0]', '$[1]', '$[2]', '$[2][0]', '$[2][1]', '$[2][2]']
    assert actual_paths == expected_paths
    
    log_msg_assert(
        "Circular reference cycle detected: current node: $[2][3], ['one', 'two', [1, "
        "2, 3, [...]]] already included as: $, ['one', 'two', [1, 2, 3, [...]]]",
        caplog
    )
    
    
def test_cs_list(child_list_cycle: JSON_ValueType, caplog: LogCaptureFixture) -> None:
    jpath_query_str = '$[*]'
    query = WellFormedValidQuery.from_str(jpath_query_str)
    
    node_list:VNodeList = query.eval(child_list_cycle)
    expected_values = [1]  # eval will not include a cycle in the result, so the cyclic parent_list is not included
    
    actual_values = list(node_list.values())
    assert len(actual_values) == len(expected_values)
    assert actual_values[0]   == expected_values[0]
    
    actual_paths = [npath.jpath_str for npath in node_list.paths() ]
    assert actual_paths == ['$[0]']

    log_msg_assert(
    "Circular reference cycle detected: current node: $[1], [1, [...]] already included as: $, [1, [...]]",
          caplog
    )

# noinspection SpellCheckingInspection
def test_ds_list(child_list_cycle: JSON_ValueType, caplog: LogCaptureFixture)-> None:
    jpath_query_str = '$..[*]'
    query = WellFormedValidQuery.from_str(jpath_query_str)
    
    node_list:VNodeList = query.eval(child_list_cycle)
    
    expected_values = [1]  # eval will not include a cycle in the result, so the cyclic parent_list is not included
    
    actual_values = list(node_list.values())
    assert len(actual_values) == len(expected_values)
    assert actual_values[0]   == expected_values[0]
    
    actual_paths = [npath.jpath_str for npath in node_list.paths() ]
    assert actual_paths == ['$[0]']
    
    log_msg_assert(
        "Circular reference cycle detected: current node: $[1], [1, [...]] already included as: $, [1, [...]]",
        caplog
    )
    
    