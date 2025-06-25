
#  File: test_rfc_examples.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
"""Test parsing against json path query strings from the tables in RFC 9535."""

from pathlib import Path
from typing import NamedTuple, Generator

import pytest

from killerbunny.lexing.lexer import JPathLexer
from killerbunny.lexing.tokens import Token
from killerbunny.parsing.parse_result import ParseResult
from killerbunny.parsing.parser import JPathParser
from killerbunny.shared.constants import ONE_MEBIBYTE, UTF8, JPATH_DATA_SEPARATOR
from killerbunny.shared.errors import Error

_MODULE_DIR = Path(__file__).parent
_TEST_FILE_DIR = _MODULE_DIR / "jpath_parser_files"

class PathAST(NamedTuple):
    file_name: str
    jpath: str
    ast_str: str

def ast_to_str(parse_result: ParseResult) -> str:
    """Return either the parse error or the parse result ASTNode as a str respresentation."""
    result_str: str = ""
    if parse_result.error:
        result_str = parse_result.error.as_test_string()
    else:
        if parse_result.node:
            result_str = str(parse_result.node)
    return result_str


def jpath_ast_data() -> Generator[ PathAST, None, None] :
    for file in _TEST_FILE_DIR.iterdir():
        if file.suffix == ".jpath_ast":
            with open(file, "r", encoding=UTF8, buffering=ONE_MEBIBYTE) as input_file:
                for line in input_file:
                    line_stripped = line.strip()
                    if line_stripped == '' or line_stripped.startswith('#'):
                        continue
                    path_ast = PathAST(file.name, *line_stripped.split(JPATH_DATA_SEPARATOR))
                    yield path_ast

@pytest.mark.parametrize("file_name, jpath, ast_str", jpath_ast_data())
def test_rfc_example(file_name: str, jpath: str, ast_str: str) -> None:
    expected = ast_str
    lexer = JPathLexer(file_name, jpath)
    tokens: list[Token]
    error: Error | None
    tokens, error = lexer.tokenize()
    assert error is None, f"Lexer should not return errors for '{jpath}'"
    assert tokens, f"Token list should not be empty for '{jpath}'"
    parser = JPathParser(tokens)
    result: ParseResult =  parser.parse()
    actual: str = ast_to_str(result)
    assert actual == expected, f"Parsing '{jpath}' should produce: {expected}"

