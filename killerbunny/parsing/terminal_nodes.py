#  File: terminal_nodes.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

import logging

from killerbunny.evaluating.value_nodes import VNodeList, VNode
from killerbunny.evaluating.evaluator_types import NormalizedJPath
from killerbunny.parsing.helper import unescape_string_content
from killerbunny.shared.json_type_defs import JSON_ValueType
from killerbunny.lexing.tokens import Token, TokenType, NUMBER_TYPES_SET
from killerbunny.parsing.node_type import ASTNode, ASTNodeType
from killerbunny.shared.jpath_bnf import JPathBNFConstants as bnf

_logger = logging.getLogger(__name__)

class LiteralNode(ASTNode):
    """Base class for literal nodes created by the parser for the AST"""
    def __init__(self, token: Token, node_type: ASTNodeType) -> None:
        super().__init__(node_type)
        self._token: Token = token
        self.set_pos(token.position.text, token.position.start, token.position.end)
    
    @property
    def token_type(self) -> TokenType:
        return self._token.token_type
    
    @property
    def token(self) -> Token:
        return self._token
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(node_type={repr(self.node_type)}, token={repr(self._token)})"
        
    def __str__(self) -> str:
        return f"{self._token.value}"


class NumericLiteralNode(LiteralNode):
    """Node for JSON number values, which can either be a Python float or int"""
    def __init__(self, token: Token) -> None:
        if token.token_type not in NUMBER_TYPES_SET:
            raise TypeError(f"Expected TokenType INT or FLOAT but received {token.token_type}")
        node_type = ASTNodeType.INT if token.token_type == TokenType.INT else ASTNodeType.FLOAT
        super().__init__(token, node_type)

    @property
    def value(self) -> int | float:
        if self._token.token_type == TokenType.FLOAT :
            return float(self._token.value)
        else:
            return int(self._token.value)
  

class StringLiteralNode(LiteralNode):
    """Node for string literals"""
    def __init__(self, token: Token) -> None:
        if token.token_type != TokenType.STRING:
            raise TypeError(f"Expected TokenType.STRING but received {token.token_type}")
        super().__init__(token, ASTNodeType.STRING)
        self._unescaped_str: str = unescape_string_content(self._token.value[1:-1])
        
    @property
    def raw_string(self) -> str:
        """Return the raw string as scanned by the lexer. This string will be quoted and may contain escape sequences.
        Use NameSelectorNode for properly processed member names. See 2.3.1.2. Semantics in RFC 9535
        """
        return self.token.value
    
    @property
    def unescaped_string(self) -> str:
        """Return the raw_string value after removing the delimiting quotes and unescaping escape sequences."""
        return self._unescaped_str
        
    
    def __str__(self) -> str:
        return self._unescaped_str

class BooleanLiteralNode(LiteralNode):
    """Node for boolean literals (true, false).
    todo - refactor so there are only two constant instances of this class, one for true and one for false, and
    refactor useages to use the constant literals instead of creating new instances
    Can we have multiple inheritance with Enum?
    """
    def __init__(self, token: Token) -> None:
        if token.token_type not in (TokenType.TRUE, TokenType.FALSE):
            raise TypeError(f"Expected TokenType TRUE or FALSE but received {token.token_type}")
        super().__init__(token, ASTNodeType.BOOLEAN_LITERAL)
        self._value: bool = token.token_type == TokenType.TRUE
        
    @property
    def value(self) -> bool:
        return self._value
        
    def __repr__(self) -> str:
        return f"BooleanLiteralNode(value={repr(self._value)}, token={repr(self.token)})"
        
    def __str__(self) -> str:
        return str(self._value).lower()


class NullLiteralNode(LiteralNode):
    """Node for the null literal."""
    def __init__(self, token: Token) -> None:
        if token.token_type != TokenType.NULL:
            raise TypeError(f"Expected TokenType.NULL but received {token.token_type}")
        super().__init__(token, ASTNodeType.NULL_LITERAL)
        # The value is implicitly Python's None. No need to store it separately
    
    def __str__(self) -> str:
        return "null"
    
    
class IdentifierNode(ASTNode):
    """Node for identifiers. Identifiers are not quoted and are used as function names,
    member-name-shorthands, and the JSON keywords true, false and null."""
    def __init__(self, token: Token) -> None:
        if not token.is_identifier():
            raise TypeError(f"Expected TokenType.IDENTIFIER but received {token.token_type}")
        super().__init__(ASTNodeType.IDENTIFIER)
        self.token: Token = token
        self.set_pos(token.position.text, token.position.start, token.position.end)
        
    @property
    def value(self) -> str:
        return self.token.value
    
    def __repr__(self) -> str:
        return f"IdentifierNode(token={repr(self.token)})"
    
    def __str__(self) -> str:
        return f"{self.token.value}"


class MemberNameShorthandNode(ASTNode):
    """The parser will normalize and convert these nodes to a name-selector wrapped in a bracketed-selection, so
    MemberNameShorthandNode is never actually part of the AST."""
    def __init__(self, token: Token) -> None:
        super().__init__(ASTNodeType.MEMBER_NAME_SHORTHAND)
        self.token: Token = token
        self.set_pos(token.position.text, token.position.start, token.position.end)
    
    def __repr__(self) -> str:
        return f"MemberNameShorthandNode(token={repr(self.token)})"
    
    def __str__(self) -> str:
        return f"member-shorthand:{self.token.value}"


class CurrentNodeIdentifier(ASTNode):
    """Used in relative-queries to refer to the current node, sybolized by at-symbol ( @ )
    See section 1.4, pg 8, RFC 9535 """
    def __init__(self, token: Token) -> None:
        if token.token_type != TokenType.AT:
            raise TypeError(f"Expected TokenType.AT but received {token.token_type}")
        super().__init__(ASTNodeType.CURRENT_NODE_ID)
        self.token: Token = token
        self.set_pos(token.position.text, token.position.start, token.position.end)
        
    @property
    def value(self) -> str:
        return self.token.value
        
    def __repr__(self) -> str:
        return f"CurrentNodeIdentifier(token={repr(self.token)})"
    
    def __str__(self) -> str:
        return bnf.CURRENT_NODE_IDENTIFIER  # '@'


class RootNode(ASTNode):
    """Represents the starting input data of a Json path evaluation, i.e., the JSON object for which to apply a
    JSON path query.
    See section 2.2, pg 14 RFC 9535
    """
    def __init__(self, token:Token) -> None:
        if token.token_type != TokenType.DOLLAR:
            raise TypeError(f"Expected TokenType.DOLLAR but received {token.token_type}")
        super().__init__(ASTNodeType.ROOT)
        self.token: Token = token  # '$'
        self.set_pos(token.position.text, token.position.start, token.position.end)
        self._json_value: JSON_ValueType  = None
        self._root_nodelist: VNodeList = VNodeList([ ])
        
        
    def __repr__(self) -> str:
        return f"RootNode(token={repr(self.token)})"
    
    def __str__(self) -> str:
        return bnf.ROOT_IDENTIFIER  # '$'
    
    @property
    def json_value(self) -> JSON_ValueType:
        return self._json_value
    
    @json_value.setter
    def json_value(self, value: JSON_ValueType) -> None:
        self._json_value = value
        self._root_nodelist  = VNodeList(
            [VNode(jpath=NormalizedJPath(bnf.ROOT_IDENTIFIER),
                   json_value=self._json_value,
                   root_value=self._json_value,
                   node_depth=0)])
    
    @property
    def root_nodelist(self) -> VNodeList:
        return self._root_nodelist
