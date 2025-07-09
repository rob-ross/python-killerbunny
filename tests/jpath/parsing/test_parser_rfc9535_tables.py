#  File: test_parser_rfc9535_tables.py
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
from killerbunny.parsing.node_type import ASTNode
from killerbunny.parsing.parse_result import ParseResult
from killerbunny.parsing.parser import JPathParser
from killerbunny.shared.constants import UTF8, ONE_MEBIBYTE

_MODULE_DIR = Path(__file__).parent
PARSER_TEST_CASES_FILENAME = "parser_test_cases.json"
_PTC_FILE_PATH = _MODULE_DIR / PARSER_TEST_CASES_FILENAME
_FILE_LIST = [_PTC_FILE_PATH, ]


@dataclass(frozen=True, slots=True)
class ParserTestCase:
    test_name         : str
    json_path         : str
    parser_ast        : str
    source_file_name  : str
    is_invalid        : bool = False
    err_msg           : str  = ""
    subparse_production: str| None = None


def data_loader() -> list[ParserTestCase]:
    test_data: list[ParserTestCase] = []
    for file_name in _FILE_LIST:
        file_path = _MODULE_DIR / file_name
        with open( file_path , encoding=UTF8, buffering=ONE_MEBIBYTE) as input_file:
            data = json.load(input_file)
            test_data.extend([ParserTestCase(**test) for test in data["tests"]])
    return test_data

def valid_paths() -> list[ParserTestCase]:
    return [ test for test in data_loader() if not test.is_invalid ]

def invalid_paths() -> list[ParserTestCase]:
    return [ test for test in data_loader() if test.is_invalid ]

EXCLUDED_TESTS_MAP: dict[str, tuple[str,str]] = {}
# during debugging of test cases, print debug info for the test names in this set
DEBUG_TEST_NAMES: set[str] = set()

@pytest.mark.parametrize("case", valid_paths(), ids=operator.attrgetter("test_name"))
def test_parser_valid_cases(case: ParserTestCase) -> None:
    """Test the cases in the parser_test_cases.json file that are intended to be grammatically correct
    and should return a result. """
    if case.test_name in EXCLUDED_TESTS_MAP:
        pytest.skip(reason=f"{EXCLUDED_TESTS_MAP[case.test_name][1]}: '{case.test_name}'")
    
    if case.test_name in DEBUG_TEST_NAMES:
        print(f"\n* * * * * test: '{case.test_name}', json_path: {case.json_path}, expected: {case.parser_ast}")
    
    assert case.json_path is not None
    lexer = JPathLexer(case.source_file_name, case.json_path)
    tokens, error = lexer.tokenize()
    assert error is None
    
    parser = JPathParser(tokens)
    result: ParseResult = parser.parse()
    assert result.error is None, f"Unexpected error when parsing {case.json_path}"
    
    ast: ASTNode | None = result.node
    assert ast is not None
    
    expected = case.parser_ast
    actual = str(ast)
    
    assert actual == expected, f"Parsing {case.json_path} should produce: {expected}"


@pytest.mark.parametrize("case", invalid_paths(), ids=operator.attrgetter("test_name"))
def test_parser_invalid_cases(case: ParserTestCase) -> None:
    """Test the cases in the parser_test_cases.json file that are intended to be not well-formed or valid"""
    if case.test_name in EXCLUDED_TESTS_MAP:
        pytest.skip(reason=f"{EXCLUDED_TESTS_MAP[case.test_name][1]}: '{case.test_name}'")
    
    assert case.json_path is not None
    lexer = JPathLexer(case.source_file_name, case.json_path)
    tokens, error = lexer.tokenize()
    assert error is None
    
    parser = JPathParser(tokens)
    result: ParseResult = parser.parse()
    assert result.error is not None, f"Expected error when parsing {case.json_path}"
    
    expected = case.err_msg
    actual   = result.error.as_test_string()
    
    assert actual == expected, f"Parsing {case.json_path} should produce: {expected}"