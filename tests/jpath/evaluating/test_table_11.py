#  File: test_table_11.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

"""Evaluate comparison expressions defined in Table 11:  "Comparison Examples".
See section 2.3.5.3., pg 30, RFC 9535
These exmples use the json object defined in rfc9535_examples/example_2.3.5.3.1.json:
{
  "obj": {"x": "y"},
  "arr": [2, 3]
}
Note that these are not  proper json path query strings; they are comparison-expression grammar productions.
We must parse the partial query strings using JPathParser.subparse().
"""
from typing import cast

import pytest
from killerbunny.evaluating.evaluator import JPathEvaluator
from killerbunny.shared.constants import ROOT_JSON_VALUE_KEY
from killerbunny.evaluating.runtime_result import RuntimeResult
from killerbunny.lexing.lexer import JPathLexer
from killerbunny.parsing.node_type import ASTNode
from killerbunny.parsing.parser import JPathParser
from killerbunny.shared.context import Context
from killerbunny.shared.errors import Error
from killerbunny.shared.json_type_defs import JSON_ValueType


@pytest.fixture(scope="module")
def value() -> JSON_ValueType:
    val =  { "obj": {"x": "y"}, "arr": [2, 3] }
    return cast(JSON_ValueType,val)

table_11_tests = [
    ("$.absent1 == $.absent2", True, "Empty nodelists are equal to each other"),
    ("$.absent1 <= $.absent2", True, "== implies <="),
    ("$.absent == 'g'", False, "Empty nodelist not equal to string literal"),
    ("$.absent1 != $.absent2", False, "Empty nodelists are equal to each other"),
    ("$.absent != 'g'", True, "Empty nodelist not equal to string literal" ),
    ("1 <= 2", True, "Numeric comparison" ),
    ("1 > 2", False, "Numeric comparison" ),
    ("13 == '13'", False, "Type Mismatch evaluates to False" ),
    ("'a' <= 'b'", True, "String comparison" ),
    ("'a' > 'b'", False, "String comparison" ),
    ("$.obj == $.arr", False, "Type mismatch" ),
    ("$.obj != $.arr", True, "Type mismatch" ),
    ("$.obj == $.obj", True, "Object comparison" ),
    ("$.obj != $.obj", False, "Object comparison" ),
    ("$.arr == $.arr", True, "Array comparison" ),
    ("$.arr != $.arr", False, "Array comparison" ),
    ("$.obj == 17", False, "Type mismatch" ),
    ("$.obj != 17", True, "Type mismatch" ),
    ("$.obj <= $.arr", False, "Objects and arrays do not offer < comparison" ),
    ("$.obj < $.arr", False, "Objects and arrays do not offer < comparison" ),
    ("$.obj <= $.obj", True, "== implies <=" ),
    ("$.arr <= $.arr", True, "== implies <=" ),
    ("1 <= $.arr", False, "Arrays do not offer < comparison" ),
    ("1 >= $.arr", False, "Arrays do not offer > comparison" ),
    ("1 > $.arr", False, "Arrays do not offer > comparison" ),
    ("1 < $.arr", False, "Arrays do not offer < comparison" ),
    ("true <= true", True, "== implies <=" ),
    ("true >= true", True, "== implies >=" ),
    ("true > true", False, "Booleans do not offer > comparison" ),
    ("true < true", False, "Booleans do not offer < comparison" ),
]
@pytest.mark.parametrize("comparison, expected, msg", table_11_tests)
def test_table_11(comparison: str, expected: bool, msg: str, value:JSON_ValueType) -> None:
    lexer = JPathLexer("test_table_11.py", comparison)
    tokens, error = lexer.tokenize()
    parser = JPathParser(tokens)
    result: tuple[ list[ tuple[str, ASTNode] ] , list[ tuple[str, Error] ] ] =  parser.subparse("comparison_expr")
    ast_node = result[0][0][1]
    context = Context('<root>')
    context.set_symbol(ROOT_JSON_VALUE_KEY, value)
    evaluator = JPathEvaluator()
    rt_result:RuntimeResult = evaluator.visit(ast_node, context)
    actual = rt_result.value
    assert actual == expected, msg