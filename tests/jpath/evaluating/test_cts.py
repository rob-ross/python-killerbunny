#  File: test_cts.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

"""
Runs test cases from the jsponpath-compliance-test_suite
https://github.com/jsonpath-standard/jsonpath-compliance-test-suite

Test Data License:

jsonpath-compliance-test-suite
The BSD-2 license (the "License") set forth below applies to all parts of the jsonpath-compliance-test-suite project. You may not use this file except in compliance with the License.

BSD-2 License

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
import json
import operator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from killerbunny.evaluating.value_nodes import VNodeList
from killerbunny.evaluating.well_formed_query import WellFormedValidQuery
from killerbunny.shared.constants import ONE_MEBIBYTE, UTF8
from killerbunny.shared.json_type_defs import JSON_ValueType


@dataclass(frozen=True, slots=True)
class CTSTestData:
    """Holds a single test case from a `cts` JSON file, and maps domain names from the test file domain to the domain names in
    RFC 9535. We also abstract away the distinction between a single test result and multiple test results for a single
    test case by just implementing a results_values and results_paths list. Test cases with a single result and path
    are represented as a single element results_values/paths list."""
    test_name    : str
    json_path    : str
    root_value   : JSON_ValueType
    is_invalid   : bool  # JSON path query string is invalid and should trigger an error
    
    # result_value : JSON_ValueType
    # result_paths : list[str]
    tags          : list[ str ]            = field(default_factory=list)
    results_values: list[ JSON_ValueType ] = field(default_factory=list)
    results_paths : list[ list[str] ]      = field(default_factory=list)
    
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CTSTestData':
        """Create a CTSTestData instance from the argument dict. `data` is assumed to be a single test case in a
        `cts` JSON file. We pop known keys from the `cts` file argument dict and replace them with key names aligned with
        RFC 9535 nomenclature."""
        kwargs = data
        test_name = kwargs.pop('name', '')
        kwargs["test_name"] = test_name
        
        json_path = kwargs.pop('selector', '')
        kwargs["json_path"] = json_path
        
        root_value = kwargs.pop('document', None)
        kwargs["root_value"] = root_value
        
        is_invalid = kwargs.pop('invalid_selector', False)
        kwargs["is_invalid"] = is_invalid
        
        results_values = kwargs.pop('results', [])
        results_paths = kwargs.pop('results_paths', [])
        
        # Handle singular result_value if present
        if 'result' in kwargs:
            result = kwargs.pop('result')
            if result is not None:
                results_values = [result]
        
        # Handle singular result_paths if present
        if 'result_paths' in kwargs:
            result_paths = kwargs.pop('result_paths')
            if result_paths is not None:
                results_paths = [result_paths]
        
        # Create the instance with normalized data
        return cls(
            **kwargs,
            results_values=results_values,
            results_paths=results_paths
        )

_MODULE_DIR = Path(__file__).parent
_CTS_FILE_PATH = _MODULE_DIR / "cts/cts.json"
_FILE_LIST = [ _CTS_FILE_PATH ]

def data_loader() -> list[CTSTestData]:
    test_data: list[CTSTestData] = []
    for file_name in _FILE_LIST:
        file_path = _MODULE_DIR / file_name
        with open( file_path , encoding=UTF8, buffering=ONE_MEBIBYTE) as input_file:
            data = json.load(input_file)
            test_data.extend( [ CTSTestData.from_dict(test) for test in data["tests"] ]  )
    return test_data

def valid_paths() -> list[CTSTestData]:
    return [ test for test in data_loader() if not test.is_invalid ]

def invalid_paths() -> list[CTSTestData]:
    return [ test for test in data_loader() if test.is_invalid ]

# (test name, reason for excluding)
EXCLUDED_TEST_NAMES = {
    ("functions, match, filter, match function, unicode char class, uppercase", "\\p{Lu} unsupported in Python re"),
    ("functions, match, filter, match function, unicode char class negated, uppercase", "\\P{Lu} unsupported in Python re"),
    ("functions, match, dot matcher on \\u2028", "dot matches \\r in Python re"),
    ("functions, match, dot matcher on \\u2029", "dot matches \\r in Python re"),
    ("functions, search, filter, search function, unicode char class, uppercase", "\\p{Lu} unsupported in Python re"),
    ("functions, search, filter, search function, unicode char class negated, uppercase", "\\P{Lu} unsupported in Python re"),
    ("functions, search, dot matcher on \\u2028", "dot matches \\r in Python re"),
    ("functions, search, dot matcher on \\u2029", "dot matches \\r in Python re"),
    # whitspace
    ("basic, no leading whitespace", "lenient whitespace allowance"),
    ("basic, no trailing whitespace", "lenient whitespace allowance"),
    ("whitespace, functions, space between function name and parenthesis", "lenient whitespace allowance"),
    ("whitespace, functions, newline between function name and parenthesis", "lenient whitespace allowance"),
    ("whitespace, functions, tab between function name and parenthesis", "lenient whitespace allowance"),
    ("whitespace, functions, return between function name and parenthesis", "lenient whitespace allowance"),
    ("whitespace, selectors, space between dot and name", "lenient whitespace allowance"),
    ("whitespace, selectors, newline between dot and name", "lenient whitespace allowance"),
    ("whitespace, selectors, tab between dot and name", "lenient whitespace allowance"),
    ("whitespace, selectors, return between dot and name", "lenient whitespace allowance"),
    ("whitespace, selectors, space between recursive descent and name", "lenient whitespace allowance"),
    ("whitespace, selectors, newline between recursive descent and name", "lenient whitespace allowance"),
    ("whitespace, selectors, tab between recursive descent and name", "lenient whitespace allowance"),
    ("whitespace, selectors, return between recursive descent and name", "lenient whitespace allowance"),
    
    
}
EXCLUDED_TESTS_MAP: dict[str, tuple[str,str]] = {  item[0]: item for item in EXCLUDED_TEST_NAMES }

# during debugging of test cases, print debug info for the test names in this set
DEBUG_TEST_NAMES = {"filter, equals number, negative zero and zero"}

@pytest.mark.parametrize("case", valid_paths(), ids=operator.attrgetter("test_name"))
def test_cts_valid(case: CTSTestData ) -> None:
    """Test the cases in the `cts` file that are intended to be well-formed and valid and should return a result. """
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


@pytest.mark.parametrize("case", invalid_paths(), ids=operator.attrgetter("test_name"))
def test_cts_invalid(case: CTSTestData ) -> None:
    """Test the cases in the `cts` file that are not well-formed or valid and should fail lexing or parsing."""
    #query = WellFormedValidQuery.from_str(case.json_path)
    if case.test_name in EXCLUDED_TESTS_MAP:
        pytest.skip(reason=f"{EXCLUDED_TESTS_MAP[case.test_name][1]}: '{case.test_name}'")
    
    if case.test_name in DEBUG_TEST_NAMES:
        print(f"\n* * * * * test: '{case.test_name}', json_root: {case.root_value}, json_path: {case.json_path}, expected: {case.results_values}")
    with pytest.raises(Exception):
        _ = WellFormedValidQuery.from_str(case.json_path)
