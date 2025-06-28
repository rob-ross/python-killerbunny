#  File: test_subparsing.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

"""Table 11 in RFC 9535 consists of comparison expressions that aren't proper JSON Path query strings. We must use
subparse('comparison_expr') to generate an AST without errors. """
import json
import operator
from dataclasses import dataclass
from pathlib import Path

import pytest

from killerbunny.lexing.lexer import JPathLexer
from killerbunny.lexing.tokens import Token
from killerbunny.parsing.node_type import ASTNode
from killerbunny.parsing.parser import JPathParser
from killerbunny.shared.constants import UTF8, ONE_MEBIBYTE
from killerbunny.shared.errors import Error

_MODULE_DIR = Path(__file__).parent
SUBPARSER_TEST_CASES_FILENAME = "subparse_test_cases_table_11.json"
_PTC_FILE_PATH = _MODULE_DIR / SUBPARSER_TEST_CASES_FILENAME
_FILE_LIST = [_PTC_FILE_PATH, ]


@dataclass(frozen=True, slots=True)
class ParserTestCase:
    test_name          : str
    json_path          : str
    parser_ast         : str
    source_file_name   : str
    is_invalid         : bool = False
    err_msg            : str  = ""
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


def subparse(tokens: list[Token], production_name: str) -> tuple[str, str | None]:
    parser = JPathParser(tokens)
    result: tuple[ list[ tuple[str, ASTNode] ] , list[ tuple[str, Error] ] ]
    result = parser.subparse(production_name)
    node_list = result[0]
    ast_str = ""
    err_list = result[1]
    err_msg = None
    for name, error in err_list:
        if name == production_name:
            err_msg = error.as_test_string()
    for name, ast_node in node_list:
        if name == production_name:
            ast_str = str(ast_node)
            
    return ast_str, err_msg

@pytest.mark.parametrize("case", valid_paths(), ids=operator.attrgetter("test_name"))
def test_subparser_valid_cases(case: ParserTestCase) -> None:
    """Test the cases in the .json test file that are intended to be sub parseable
    and should return a result. """
    if case.test_name in EXCLUDED_TESTS_MAP:
        pytest.skip(reason=f"{EXCLUDED_TESTS_MAP[case.test_name][1]}: '{case.test_name}'")
    
    if case.test_name in DEBUG_TEST_NAMES:
        print(f"\n* * * * * test: '{case.test_name}', json_path: {case.json_path}, expected: {case.parser_ast}")
    
    assert case.json_path is not None
    lexer = JPathLexer(case.source_file_name, case.json_path)
    tokens, error = lexer.tokenize()
    assert error is None
    
    assert case.subparse_production is not None
    ast_str, err_msg = subparse(tokens, case.subparse_production)
    assert err_msg is None
    
    assert ast_str == case.parser_ast, f"Parsing {case.json_path} should produce: {case.parser_ast}"

# the following is commented out to supress pytest reporting of this skipped test.

# @pytest.mark.skip("No invalid cases exist in the test file. ")
# @pytest.mark.parametrize("case", invalid_paths(), ids=operator.attrgetter("test_name"))
# def test_subparser_invalid_cases(case: ParserTestCase) -> None:
#     """Test the cases in the .json test file that are intended to not be sub-parseable with the given production name."""
#     if case.test_name in EXCLUDED_TESTS_MAP:
#         pytest.skip(reason=f"{EXCLUDED_TESTS_MAP[case.test_name][1]}: '{case.test_name}'")
#
#     assert case.json_path is not None
#     lexer = JPathLexer(case.source_file_name, case.json_path)
#     tokens, error = lexer.tokenize()
#     assert error is None
#
#     parser = JPathParser(tokens)
#     result: ParseResult = parser.parse()
#     assert result.error is not None, f"Expected error when parsing {case.json_path}"
#
#     assert case.subparse_production is not None
#     ast_str, err_msg = subparse(tokens, case.subparse_production)
#     assert err_msg is not None
#
#     expected = case.err_msg
#     actual   = err_msg
#
#     assert actual == expected, f"Subparsing {case.json_path} should produce error: {expected}"