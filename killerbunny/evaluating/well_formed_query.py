#  File: well_formed_query.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#
import logging
from typing import TYPE_CHECKING

from killerbunny.evaluating.evaluator import JPathEvaluator
from killerbunny.lexing.lexer import JPathLexer
from killerbunny.parsing.parser import JPathParser
from killerbunny.shared.constants import JPATH_QUERY_RESULT_NODE_KEY
from killerbunny.shared.context import Context


if TYPE_CHECKING:
    from killerbunny.evaluating.value_nodes import VNodeList
    from killerbunny.parsing.node_type import ASTNode
    from killerbunny.shared.json_type_defs import JSON_ValueType


_logger = logging.getLogger(__name__)

class WellFormedValidQuery:
    
    _query_node: 'ASTNode'
    
    def __init__(self, query_node: 'ASTNode') -> None:
        """Users should not instantiate this class directly and should instead use the factory method
        WellFormedValidQuery.from_str in this same class to ensure that the query_node is well-formed and valid.
        """
        # todo maybe we can nest this class in the Parser so it can only be obtained from the parser after  successful
        # parse?
        if query_node is None:
            raise ValueError("query_node cannot be None")
        self._query_node = query_node
        
    @classmethod
    def from_str(cls, jpath_query_string: str) -> 'WellFormedValidQuery':
        """Attempt to parse the jpath query string and return a WellFormedValidQuery instance. If the query string is
        not well-formeed nor valid, raise an Exception"""
        if not jpath_query_string:
            raise ValueError("jpath_query_string cannot be None nor empty")
        lexer = JPathLexer("",jpath_query_string)
        tokens, error = lexer.tokenize()
        if error:
            raise ValueError(error.as_string())
        parser = JPathParser(tokens)
        parse_result = parser.parse()
        if parse_result.error:
            raise ValueError(parse_result.error.as_string())
        if not parse_result.node:
            raise AssertionError(f"Parsing returned no errors, but ASTNode is None for {jpath_query_string}")
        return WellFormedValidQuery(parse_result.node)
    
    
    def eval(self, root_value: 'JSON_ValueType') -> 'VNodeList':
        context = Context.root(root_value)
        rt_result =  JPathEvaluator().visit(self._query_node, context )
        if rt_result.error:
            _logger.warning(rt_result.error.as_string())
            raise rt_result.error  # todo remove in production. We fail-fast during development
        assert rt_result.value is not None
        output_value = context.get_symbol(JPATH_QUERY_RESULT_NODE_KEY)
        return output_value
