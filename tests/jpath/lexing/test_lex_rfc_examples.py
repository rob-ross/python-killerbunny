
#  File: test_rfc_examples.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

"""Test lexing against json path query strings from the tables in RFC 9535."""
from pathlib import Path
from typing import NamedTuple, Generator

import pytest

from killerbunny.lexing.lexer import JPathLexer
from killerbunny.lexing.tokens import Token
from killerbunny.shared.constants import ONE_MEBIBYTE, UTF8, JPATH_DATA_SEPARATOR
from killerbunny.shared.errors import Error

_MODULE_DIR = Path(__file__).parent
_TEST_FILE_DIR = _MODULE_DIR / "jpath_token_files"

class PathTokens(NamedTuple):
    file_name: str
    jpath: str
    tokens_str: str
    
def tokens_to_str(tokens: list[Token], error: Error | None) -> str:
    result_str: str = ""
    if error:
        result_str = error.as_test_string()
    else:
        if tokens:
            result_str = ', '.join( t.__testrepr__() for t in tokens)
    return result_str
    
def jpath_tokens_data() -> Generator[ PathTokens, None, None] :
    for file in _TEST_FILE_DIR.iterdir():
        if file.suffix == ".jpath_tokens":
            with open(file, "r", encoding=UTF8, buffering=ONE_MEBIBYTE) as input_file:
                for line in input_file:
                    line_stripped = line.strip()
                    if line_stripped == '' or line_stripped.startswith('#'):
                        continue
                    path_tokens = PathTokens(file.name, *line_stripped.split(JPATH_DATA_SEPARATOR))
                    yield path_tokens
    
@pytest.mark.parametrize("file_name, jpath, tokens_str", jpath_tokens_data())
def test_rfc_example(file_name: str, jpath: str, tokens_str: str) -> None:
    expected = tokens_str
    lexer = JPathLexer(file_name, jpath)
    tokens, error = lexer.tokenize()
    assert error is None
    actual = tokens_to_str(tokens, error)
    assert actual == expected, f"{jpath} should produce: {expected}"

    