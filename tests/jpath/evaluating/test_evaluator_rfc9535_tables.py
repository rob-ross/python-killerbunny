#  File: test_evaluator_rfc9535_tables.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

"""
RFC 9535 includes multiple tables with example paths and their expected results. The tests here implement all examples
that are intended to be evaluated without generating errors. These are tables 2-18, except for:
    Table 11 - which are comparison_expressions and not valid query paths, and are tested separately in test_table_11.py
    Table 14 - which tests for well-formed function declarations and not evaluation results, and
    Table 18 - which are examples of NormalizedPaths and are not associated with any query parameter data
"""
import json
import operator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from killerbunny.evaluating.value_nodes import VNodeList
from killerbunny.evaluating.well_formed_query import WellFormedValidQuery
from killerbunny.shared.constants import ONE_MEBIBYTE, UTF8
from killerbunny.shared.json_type_defs import JSON_ValueType


@dataclass(frozen=True, slots=True)
class EvaluatorTestCase:
    test_name         : str
    json_path         : str
    root_value        : JSON_ValueType
    source_file_name  : str
    is_invalid        : bool = False
    err_msg           : str  = ""
    subparse_production: str| None = None
    results_values: list[ JSON_ValueType ] = field(default_factory=list)
    results_paths : list[ list[str] ]      = field(default_factory=list)

_MODULE_DIR = Path(__file__).parent
_EVAL_TESTS_FILE_PATH = _MODULE_DIR / "evaluator_test_cases.json"
_FILE_LIST = [ _EVAL_TESTS_FILE_PATH ]

def data_loader() -> list[EvaluatorTestCase]:
    test_data: list[EvaluatorTestCase] = []
    for file_name in _FILE_LIST:
        file_path = _MODULE_DIR / file_name
        with open( file_path , encoding=UTF8, buffering=ONE_MEBIBYTE) as input_file:
            data = json.load(input_file)
            test_data.extend( [ EvaluatorTestCase(**test) for test in data["tests"] ]  )
    return test_data

def valid_paths() -> list[EvaluatorTestCase]:
    return [ test for test in data_loader() if not test.is_invalid ]

def invalid_paths() -> list[EvaluatorTestCase]:
    return [ test for test in data_loader() if test.is_invalid ]

EXCLUDED_TEST_NAMES: list[tuple[str, str]] = []  # [(test name, reason for excluding)]
EXCLUDED_TESTS_MAP: dict[str, tuple[str,str]] = {  item[0]: item for item in EXCLUDED_TEST_NAMES }

# during debugging of test cases, print debug info for the test names in this set
DEBUG_TEST_NAMES: set[str] = set()

@pytest.mark.parametrize("case", valid_paths(), ids=operator.attrgetter("test_name"))
def test_cts_valid(case: EvaluatorTestCase ) -> None:
    """Test the cases in the `_EVAL_TESTS_FILE_PATH` file that are intended to be well-formed and valid and
    should return a result. """
    if case.test_name in EXCLUDED_TESTS_MAP:
        pytest.skip(reason=f"{EXCLUDED_TESTS_MAP[case.test_name][1]}: '{case.test_name}'")
    
    if case.test_name in DEBUG_TEST_NAMES:
        print(f"\n* * * * * test: '{case.test_name}', json_root: {case.root_value}, json_path: {case.json_path}, expected: {case.results_values}")
    
    assert case.root_value is not None
    query = WellFormedValidQuery.from_str(case.json_path)
    actual_nodelist:VNodeList = query.eval(case.root_value)
    actual_values = list(actual_nodelist.values())
    assert actual_values in case.results_values, \
        f"Actual values {actual_values} not found in expected results_values {case.results_values}"
    actual_paths_str = [npath.jpath_str for npath in actual_nodelist.paths()]
    assert actual_paths_str in case.results_paths, \
        f"Actual paths {actual_paths_str} not found in expected results_paths {case.results_paths}"