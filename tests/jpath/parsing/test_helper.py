#  File: test_helper.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

""" Test methods in helper.py"""
import pytest

from killerbunny.parsing.helper import escape_string_content

escape_char_for_jsonpath_tests = [
    ("$['a'']", r"$['a\'']", "Embedded Single quote is properly escaped"),
    ("$['\\']", "$['\\\\']", "Backslash is  properly escaped"),
]
@pytest.mark.parametrize("text, expected, msg", escape_char_for_jsonpath_tests)
def test_escape_char_for_jsonpath(text: str, expected: str, msg: str) -> None:
    actual = escape_string_content(text)
    assert actual == expected, msg