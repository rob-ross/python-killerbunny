#  File: test_lexer_rfc9535_tables.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
import json
import operator
from dataclasses import dataclass
from pathlib import Path

import pytest

from killerbunny.lexing.lexer import JPathLexer
from killerbunny.lexing.tokens import Token
from killerbunny.shared.constants import UTF8, ONE_MEBIBYTE
from killerbunny.shared.errors import Error

_MODULE_DIR = Path(__file__).parent
LEXER_TEST_CASES_FILENAME = "lexer_test_cases.json"
_LTC_FILE_PATH = _MODULE_DIR / LEXER_TEST_CASES_FILENAME
_FILE_LIST = [ _LTC_FILE_PATH,]

@dataclass(frozen=True, slots=True)
class LexerTestCase:
    test_name         : str
    json_path         : str
    lexer_tokens      : str
    source_file_name  : str
    is_invalid        : bool = False


def data_loader() -> list[LexerTestCase]:
    test_data: list[LexerTestCase] = []
    for file_name in _FILE_LIST:
        file_path = _MODULE_DIR / file_name
        with open( file_path , encoding=UTF8, buffering=ONE_MEBIBYTE) as input_file:
            data = json.load(input_file)
            test_data.extend( [ LexerTestCase(**test) for test in data["tests"] ]  )
    return test_data

def valid_paths() -> list[LexerTestCase]:
    return [ test for test in data_loader() if not test.is_invalid ]

def invalid_paths() -> list[LexerTestCase]:
    return [ test for test in data_loader() if test.is_invalid ]

def tokens_to_str(tokens: list[Token], error: Error | None) -> str:
    result_str: str = ""
    if error:
        result_str = error.as_test_string()
    else:
        if tokens:
            result_str = ', '.join( t.__testrepr__() for t in tokens)
    return result_str

EXCLUDED_TESTS_MAP: dict[str, tuple[str,str]] = {}
# during debugging of test cases, print debug info for the test names in this set
DEBUG_TEST_NAMES: set[str] = set()

@pytest.mark.parametrize("case", valid_paths(), ids=operator.attrgetter("test_name"))
def test_lexer_valid_cases(case: LexerTestCase ) -> None:
    """Test the cases in the lexer_tests file that are intended to be syntactially correct and should return a result. """
    if case.test_name in EXCLUDED_TESTS_MAP:
        pytest.skip(reason=f"{EXCLUDED_TESTS_MAP[case.test_name][1]}: '{case.test_name}'")
    
    if case.test_name in DEBUG_TEST_NAMES:
        print(f"\n* * * * * test: '{case.test_name}', json_path: {case.json_path}, expected: {case.lexer_tokens}")
    
    assert case.json_path is not None
    lexer = JPathLexer(case.source_file_name, case.json_path)
    tokens, error = lexer.tokenize()
    assert error is None
    
    expected = case.lexer_tokens
    actual = tokens_to_str(tokens, error)

    assert actual == expected, f"{case.json_path} should produce: {expected}"