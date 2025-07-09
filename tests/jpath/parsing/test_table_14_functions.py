#  File: test_table_14_functions.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
"""Table 14 in RFC 9535 references arbitrary functions bar(), bnl(), blt() and bal() but are not registered functions.
 This test creates these functions and registers them so we can test them for well-formness and validity as indicated
 in Table 14.
 """
import operator
from dataclasses import dataclass

import pytest

from killerbunny.lexing.lexer import JPathLexer
from killerbunny.parsing.function import FunctionNode, FunctionParam, FunctionParamType, VALUE_TYPES, ValueType, \
    LogicalType, NodesType, register_function
from killerbunny.parsing.node_type import ASTNode
from killerbunny.parsing.parse_result import ParseResult
from killerbunny.parsing.parser import JPathParser


####################################################################
# FUNCTION DEFINITIONS
####################################################################

class BarFunction1(FunctionNode):
    def __init__(self) -> None:
        return_param = FunctionParam("return",  FunctionParamType.LogicalType, LogicalType)
        param1 = FunctionParam("value", FunctionParamType.ValueType, VALUE_TYPES )
        super().__init__("bar", return_param, [param1])
    
    def eval(self,value: ValueType) -> LogicalType:  # type: ignore
        return LogicalType.value_for( True )

class BarFunction2(FunctionNode):
    def __init__(self) -> None:
        return_param = FunctionParam("return",  FunctionParamType.LogicalType, LogicalType)
        param1 = FunctionParam("value", FunctionParamType.NodesType, NodesType )
        super().__init__("bar", return_param, [param1])
    
    def eval(self,value: NodesType) -> LogicalType:  # type: ignore
        return LogicalType.value_for( True )

class BarFunction3(FunctionNode):
    def __init__(self) -> None:
        return_param = FunctionParam("return",  FunctionParamType.LogicalType, LogicalType)
        param1 = FunctionParam("value", FunctionParamType.LogicalType, LogicalType )
        super().__init__("bar", return_param, [param1])
    
    def eval(self,value: LogicalType) -> LogicalType:  # type: ignore
        return LogicalType.value_for( True )


class BnlFunction1(FunctionNode):
    def __init__(self) -> None:
        return_param = FunctionParam("return", FunctionParamType.LogicalType, LogicalType)
        param1 = FunctionParam("nodes", FunctionParamType.NodesType, NodesType)
        super().__init__("bnl", return_param, [param1])
        self.test_name = "bnl1"
    
    def eval(self, param1: NodesType) -> LogicalType:  # type: ignore
        return LogicalType.value_for(True)


class BnlFunction2(FunctionNode):
    def __init__(self) -> None:
        return_param = FunctionParam("return", FunctionParamType.LogicalType, LogicalType)
        param1 = FunctionParam("param1", FunctionParamType.LogicalType, LogicalType )
        super().__init__("bnl", return_param, [param1])
        self.test_name = "bnl2"
    
    def eval(self, param1: LogicalType) -> LogicalType:  # type: ignore
        return LogicalType.value_for(True)


class BltFunction(FunctionNode):
    def __init__(self) -> None:
        return_param = FunctionParam("return", FunctionParamType.LogicalType, LogicalType)
        param1 = FunctionParam("param1", FunctionParamType.LogicalType, LogicalType )
        super().__init__("blt", return_param, [param1])
        
    def eval(self, param1: LogicalType) -> LogicalType:  # type: ignore
        return LogicalType.value_for(True)
    

class BalFunction(FunctionNode):
    def __init__(self) -> None:
        return_param = FunctionParam("return", FunctionParamType.LogicalType, LogicalType)
        param1 = FunctionParam("value", FunctionParamType.ValueType, VALUE_TYPES)
        super().__init__("bal", return_param, [param1])
    
    def eval(self, value: ValueType) -> LogicalType:  # type: ignore
        return LogicalType.value_for(True)


@dataclass(frozen=True, slots=True)
class ParserTestCase:
    test_name         : str
    json_path         : str
    parser_ast        : str
    source_file_name  : str
    is_invalid        : bool = False
    err_msg           : str  = ""
    function          : FunctionNode | None = None
    
    
def parse_helper(case: ParserTestCase)-> ParseResult:
    assert case.json_path is not None, f"JSON Query string cannot be None"
    lexer = JPathLexer(case.source_file_name, case.json_path)
    tokens, error = lexer.tokenize()
    assert error is None, f"Unexpected error while lexing: {error}"
    
    parser = JPathParser(tokens)
    result: ParseResult = parser.parse()
    return result

bar_test_cases: list[ParserTestCase] = [
    ParserTestCase("bar1-$[?bar(@.a)]", "$[?bar(@.a)]", "${CS{bs[fs{?bar(@ segments<CS{bs[ns:a]/bs}/CS>)->LogicalType}/fs]/bs}/CS}/$", "table_14.jpathl", False, "", BarFunction1()),
    ParserTestCase("bar2-$[?bar(@.a)]", "$[?bar(@.a)]", "${CS{bs[fs{?bar(@ segments<CS{bs[ns:a]/bs}/CS>)->LogicalType}/fs]/bs}/CS}/$", "table_14.jpathl", False, "", BarFunction2()),
    ParserTestCase("bar3-$[?bar(@.a)]", "$[?bar(@.a)]", "${CS{bs[fs{?bar(@ segments<CS{bs[ns:a]/bs}/CS>)->LogicalType}/fs]/bs}/CS}/$", "table_14.jpathl", False, "", BarFunction3()),
]
@pytest.mark.parametrize("case", bar_test_cases, ids=operator.attrgetter("test_name"))
def test_bar_cases(case: ParserTestCase) -> None:
    assert case.function is not None
    register_function(case.function)
    result = parse_helper(case)
    if case.is_invalid:
        assert result.error is not None, f"Error was none, expected error: {result.error}"
        assert result.error.as_test_string() == case.err_msg , f"Expect error message to be '{case.err_msg}'"
    else:
        assert result.error is None, f"Expected no error, got: {result.error}"
        assert result.node is not None, f"ASTNode was none, expected node: {case.parser_ast}"
        ast_node: ASTNode = result.node
        assert str(ast_node) == case.parser_ast, f"Expected ASTNode to be '{case.parser_ast}', got '{str(ast_node)}'"
        
        

bnl_test_cases: list[ ParserTestCase ] = [
    ParserTestCase("bnl1-$[?bnl(@.*)]", "$[?bnl(@.*)]", "${CS{bs[fs{?bnl(@ segments<CS{bs[*]/bs}/CS>)->LogicalType}/fs]/bs}/CS}/$", "table_14.jpathl", False, "", BnlFunction1() ),
    ParserTestCase("bnl2-$[?bnl(@.*)]", "$[?bnl(@.*)]", "${CS{bs[fs{?bnl(@ segments<CS{bs[*]/bs}/CS>)->LogicalType}/fs]/bs}/CS}/$", "table_14.jpathl", False, "", BnlFunction2() ),
]
@pytest.mark.parametrize("case", bnl_test_cases, ids=operator.attrgetter("test_name"))
def test_bnl_cases(case: ParserTestCase) -> None:
    
    assert case.function is not None
    register_function(case.function)
    
    result = parse_helper(case)
    if case.is_invalid:
        assert result.error is not None, f"Error was none, expected error: {result.error}"
        assert result.error.as_test_string() == case.err_msg , f"Expect error message to be '{case.err_msg}'"
    else:
        assert result.error is None, f"Expected no error, got: {result.error}"
        assert result.node is not None, f"ASTNode was none, expected node: {case.parser_ast}"
        ast_node: ASTNode = result.node
        assert str(ast_node) == case.parser_ast, f"Expected ASTNode to be {case.parser_ast}, got '{str(ast_node)}'"
        

blt_test_cases: list[ParserTestCase] = [
    ParserTestCase("blt-$[?blt(1==1)]", "$[?blt(1==1)]", "${CS{bs[fs{?blt(comp_expr(1, ==, 1))->LogicalType}/fs]/bs}/CS}/$", "table_14.jpathl"),
    ParserTestCase("blt-$[?blt(1)]",    "$[?blt(1)]",    "", "table_14.jpathl", True, 'Validation Error: function_expr: Expected LogicalType but got ValueType at position 8: $[?blt(^1^)]'),
]
@pytest.mark.parametrize("case", blt_test_cases, ids=operator.attrgetter("test_name"))
def test_blt_cases(case: ParserTestCase) -> None:
    register_function(BltFunction())
    
    result = parse_helper(case)
    if case.is_invalid:
        assert result.error is not None, f"Error was none, expected error: {result.error}"
        assert result.error.as_test_string() == case.err_msg , f"Expect error message to be '{case.err_msg}'"
    else:
        assert result.error is None, f"Expected no error, got: {result.error}"
        assert result.node is not None, f"ASTNode was none, expected node: {case.parser_ast}"
        ast_node: ASTNode = result.node
        assert str(ast_node) == case.parser_ast, f"Expected ASTNode to be {case.parser_ast}, got '{str(ast_node)}'"



bal_test_cases: list[ParserTestCase] = [
    ParserTestCase("bal-$[?bal(1)]", "$[?bal(1)]", "${CS{bs[fs{?bal(1)->LogicalType}/fs]/bs}/CS}/$", "table_14.jpathl"),
]
@pytest.mark.parametrize("case", bal_test_cases, ids=operator.attrgetter("test_name"))
def test_bal_cases(case: ParserTestCase) -> None:
    register_function(BalFunction())
    
    result = parse_helper(case)
    if case.is_invalid:
        assert result.error is not None, f"Error was none, expected error: {result.error}"
        assert result.error.as_test_string() == case.err_msg, f"Expect error message to be '{case.err_msg}'"
    else:
        assert result.error is None, f"Expected no error, got: {result.error}"
        assert result.node is not None, f"ASTNode was none, expected node: {case.parser_ast}"
        ast_node: ASTNode = result.node
        assert str(ast_node) == case.parser_ast, f"Expected ASTNode to be {case.parser_ast}, got '{str(ast_node)}'"