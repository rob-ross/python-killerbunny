#  File: test_pretty_printer_cycles.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#




"""Test that cycles in the graph being printed are identified and do not cause infinite recursion or stack overflow."""
import logging
from typing import Any

from _pytest.logging import LogCaptureFixture

# noinspection PyProtectedMember
from killerbunny.incubator.jsonpointer.pretty_printer import _pp_list, FormatFlags, _pp_dict


# noinspection SpellCheckingInspection
def test_cycle_list_in_list(caplog: LogCaptureFixture) -> None:
    parent_list: list[Any] = [ 1 ]
    cycle_list = parent_list
    parent_list.append(cycle_list)  # creates a cycle
    
    lines = [""]
    caplog.set_level(logging.WARN)
    actual = _pp_list(parent_list, FormatFlags(), lines)  # this should log a warning about the cycle
    expected: list[Any] = ['[', ' 1,', ' [...]', ' ]']
    assert actual == expected
    
    # 1. Check that at least one log message was captured
    assert len(caplog.records) == 1
    # 2. Get the first captured record
    record = caplog.records[0]
    # 3. Assert on the details of the record
    assert record.levelname == "WARNING"
    assert "Cycle detected in json_list: [1, [...]]" in record.message

# noinspection SpellCheckingInspection
def test_cycle_dict_in_list(caplog: LogCaptureFixture) -> None:
    parent_list: list[Any] = [ 1 ]
    dict_: dict[str, Any] = { "one" : 1 }
    cycle_dict = dict_
    dict_["two"] = cycle_dict
    parent_list.append(dict_)
    
    lines = [""]
    caplog.set_level(logging.WARN)
    actual = _pp_list(parent_list, FormatFlags(), lines)  # this should log a warning about the cycle
    expected: list[Any] = ['[', ' 1,', ' {', ' one: 1,', ' two:', ' {...}', ' }', ' ]']
    assert actual == expected
    
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    assert "Cycle detected in json_dict: {'one': 1, 'two': {...}}" in record.message

# noinspection SpellCheckingInspection
def test_cycle_dict_in_dict(caplog: LogCaptureFixture) -> None:
    dict_: dict[str, Any] = { "one" : 1 }
    cycle_dict = dict_
    dict_["two"] = cycle_dict
    
    lines = [""]
    caplog.set_level(logging.WARN)
    actual = _pp_dict(dict_, FormatFlags(), lines)  # this should log a warning about the cycle
    expected: list[Any] = ['{', ' one: 1,', ' two:', ' {...}', ' }']
    assert actual == expected
    
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    assert "Cycle detected in json_dict: {'one': 1, 'two': {...}}" in record.message

# noinspection SpellCheckingInspection
def test_cycle_list_in_dict(caplog: LogCaptureFixture) -> None:
    list_: list[Any] = [1]
    cycle_list = list_
    list_.append(cycle_list)  # creates a cycle
    dict_: dict[str, Any] = { "one" : 1, "two":list_ }
    
    lines = [""]
    caplog.set_level(logging.WARN)
    actual = _pp_dict(dict_, FormatFlags(), lines)  # this should log a warning about the cycle
    expected: list[Any] = ['{', ' one: 1,', ' two:', ' [', ' 1,', ' [...]', ' ]', ' }']
    assert actual == expected
    
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    assert "Cycle detected in json_list: [1, [...]]" in record.message


