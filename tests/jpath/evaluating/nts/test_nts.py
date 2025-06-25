#  File: test_nts.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

"""
Runs test cases fromjsonpath-compliance-normalized-paths
https://github.com/jg-rp/jsonpath-compliance-normalized-paths/blob/c9288b33aae7440fa1d8ee8cc0a150a47f4d5c96/LICENSE

normalized_paths.json released under BSD 2-Clause "Simplified" License

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from killerbunny.shared.constants import UTF8, ONE_MEBIBYTE
from killerbunny.shared.json_type_defs import JSON_ValueType

# maps key names from test data file to common nomenclature
TEST_PROPERTY_MAP: dict[str, str] = {
    "name": "test_name", "query": "json_path", "document": "root_value"
}

@dataclass(frozen=True, slots=True)
class CTSTestData:
    """Holds a single test case from a normalizd_paths json file, and maps domain names from the test file domain
    to the domain names in  RFC 9535.
    We also abstract away the distinciton between a single test result and multiple test results for a single
    test case by just implementing a results_values and results_paths list. Test cases with a single result and path
    are represented as a single element results_values/paths list."""
    test_name    : str
    json_path    : str
    root_value   : JSON_ValueType

    results_values: list[ JSON_ValueType ] = field(default_factory=list)  # null in test data file, only tests paths
    results_paths : list[ list[str] ]      = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CTSTestData':
        """Create a CTSTestData instance from the argument dict. `data` is assumed to be a single test case in a
        cts json file. We pop known keys from the cts file argument dict and replace them with key names aligned with
        RFC 9535 nomenclature."""
        kwargs = data
        for k in TEST_PROPERTY_MAP:
            value = kwargs.pop(k, '')
            mapped_key = TEST_PROPERTY_MAP[k]
            kwargs[mapped_key] = value
            
        result_paths = kwargs.pop('paths', [])
        results_paths = [result_paths]
        
        # Create the instance with normalized data
        return cls(
            **kwargs,
            results_paths=results_paths
        )

_MODULE_DIR = Path(__file__).parent
_TEST_FILE_PATH = _MODULE_DIR / "normalized_paths.json"
_FILE_LIST = [_TEST_FILE_PATH]

def data_loader() -> list[CTSTestData]:
    test_data: list[CTSTestData] = []
    for file_name in _FILE_LIST:
        file_path = _MODULE_DIR / file_name
        with open( file_path , encoding=UTF8, buffering=ONE_MEBIBYTE) as input_file:
            data = json.load(input_file)
            test_data.extend( [ CTSTestData.from_dict(test) for test in data["tests"] ]  )
    return test_data


# todo we need to implement a Normalize function in order to run the tests against it

# @pytest.mark.parametrize("case", data_loader(), ids=operator.attrgetter("test_name"))
# def test_normalized_paths(case: CTSTestData ) -> None:
#     assert case.root_value is not None
#     query = WellFormedValidQuery.from_str(case.json_path)
#     actual_nodelist:VNodeList = query.eval(case.root_value)
#     actual_values = list(actual_nodelist.values())
#     assert actual_values in case.results_values, \
#         f"Actual values {actual_values} not found in expected results_values {case.results_values}"
#     actual_paths_str = [npath.jpath_str for npath in actual_nodelist.paths()]
#     assert actual_paths_str in case.results_paths, \
#         f"Actual paths {actual_paths_str} not found in expected results_paths {case.results_paths}"