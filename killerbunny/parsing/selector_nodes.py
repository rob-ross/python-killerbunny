#  File: selector_nodes.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

import logging

from killerbunny.lexing.tokens import Token, TokenType
from killerbunny.parsing.helper import unescape_string_content
from killerbunny.parsing.node_type import ASTNode, ASTNodeType
from killerbunny.shared.jpath_bnf import JPathBNFConstants

_logger = logging.getLogger(__name__)


####################################################################
# SELECTORS
####################################################################

class SelectorNode(ASTNode):
    """Base class for all selector nodes
    selector ::= name_selector:STRING_LITERAL |
                 "*" |
                 slice_selector |
                 index_selector:INT_LITERAL |
                 filter_selector
    """
    def __init__(self, token: Token, node_type: ASTNodeType) -> None:
        super().__init__(node_type)
        self.token: Token = token
        self.set_pos(token.position.text, token.position.start, token.position.end)
        
        
class NameSelectorNode(SelectorNode):
    """Node for name-selector, to hold a member-name. Only TokenType.STRING types are allowed in the constructor
    
    name-selector ::=  string_literal
    
    2.3.1.2. Semantics, pg 18, RFC 9535
    A name-selector string MUST be converted to a member name M by removing the surrounding quotes and replacing each
    escape sequence with its equivalent Unicode character, as shown in Table 4
    
    The initializer of this class ensures the above processing occurs to the string_literal in the `token` argument.
    Calling `member_name` on this instance returns a string that complies with the above specification. I.e, you may
    use the returned value as-is as a lookup in any JSON object (I.e., Python dict)
    
    :raise TypeError if token.token_type is not TokenType.STRING
    """
    def __init__(self, token: Token) -> None:
        if token.token_type != TokenType.STRING:
            raise TypeError(f"NameSelectorNode only accepts TokenType.STRING tokens, but received {token.token_type}")
        super().__init__(token, ASTNodeType.NAME_SELECTOR)
        self._member_name = self._make_member_name()
    
    @property
    def member_name(self) -> str:
        return self._member_name
    
    def __repr__(self) -> str:
        return f"NameSelectorNode(token={repr(self.token)}, member_name={repr(self._member_name)})"
    
    def __str__(self) -> str:
        return f"{self._node_type.abbreviation}:{self._member_name}"
    
    def _make_member_name(self) -> str:
        if not self.token.value:
            return self.token.value
    
        tv = self.token.value
        
        # Based on lexer guarantees:
        # - len(tv) >= 2, because the empty string will be represented as "" or '' in token.value
        # - tv[0] and tv[-1] in STRING_DELIMETER_SET ( ", ' )
        # - tv[0] == tv[-1] (ensured by lexer)
        # Therefore, we can directly strip the quotes.
        content_to_unescape = tv[1:-1]
        
        # The unescape_string_content function handles internal errors gracefully
        # by returning the original problematic sequence part, so an outer try-except
        # for ValueError from it is not strictly necessary here.
        member_name = unescape_string_content(content_to_unescape)
        
        return member_name


class WildcardSelectorNode(SelectorNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token, ASTNodeType.WILDCARD_SELECTOR)
        
    def __repr__(self) -> str:
        return f"WildcardSelectorNode(token={repr(self.token)})"
        
    def __str__(self) -> str:
        return "*"
    


class SliceSelectorNode(SelectorNode):
    def __init__(self, token: Token, start: int | None, end: int | None, step: int | None) -> None:
        """Token is last token in series of tokens that make up the slice selector, either a colon or INT"""
        super().__init__(token, ASTNodeType.SLICE_SELECTOR)
        if start:
            if start < JPathBNFConstants.INT_MIN:
                raise IndexError("Start value is less than the minimum allowed value.")
            if start > JPathBNFConstants.INT_MAX:
                raise IndexError("Start value is greater than the maximum allowed value.")
        if end:
            if end < JPathBNFConstants.INT_MIN:
                raise IndexError("End value is less than the minimum allowed value.")
            if end > JPathBNFConstants.INT_MAX:
                raise IndexError("End value is greater than the maximum allowed value.")
        if step:
            if step < JPathBNFConstants.INT_MIN:
                raise IndexError("Step value is less than the minimum allowed value.")
            if step > JPathBNFConstants.INT_MAX:
                raise IndexError("Step value is greater than the maximum allowed value.")
            
        self._start: int | None = start
        self._end: int | None   = end
        self._step: int | None  = step
        
    @property
    def slice_op(self) -> slice:
        """Return a slice object from the node's state. """
        return slice(self._start, self._end, self._step)
    
    def __repr__(self) -> str:
        repr_str = f"SliceSelectorNode(start={repr(self._start)}, end={repr(self._end)}, step={repr(self._step)})"
        return repr_str
    
    def __str__(self) -> str:
        start_str = self._start if self._start is not None else ''
        end_str   = self._end   if self._end   is not None else ''
        step_str  = self._step  if self._step  is not None else ''

        repr_str = f"{start_str}:{end_str}:{step_str}"
        return f"{self._node_type.abbreviation}({repr_str})"
    
 

class IndexSelectorNode(SelectorNode):
    def __init__(self, token: Token) -> None:
        """Token type should be INT"""
        if token.token_type != TokenType.INT:
            raise TypeError(f"Expected int token, but received {token.token_type}")
        super().__init__(token, ASTNodeType.INDEX_SELECTOR)
        self._index: int = int(token.value)  # todo handle erorrs
        if self._index:
            if self._index < JPathBNFConstants.INT_MIN:
                raise IndexError("Index value is less than the minimum allowed value.")
            if self._index > JPathBNFConstants.INT_MAX:
                raise IndexError("Index value is greater than the maximum allowed value.")

    @property
    def index(self) -> int:
        return self._index
    
    def __repr__(self) -> str:
        return f"IndexSelectorNode(index={repr(self._index)})"
    
    def __str__(self) -> str:
        return f"{self._node_type.abbreviation}:{self._index}"


class FilterSelectorNode(SelectorNode):
    def __init__(self, logical_expr_node: ASTNode) -> None:
        super().__init__(Token.NO_TOKEN, ASTNodeType.FILTER_SELECTOR)  # todo implement
        self.logical_expr_node = logical_expr_node
        
    def __repr__(self) -> str:
        return f"FilterSelectorNode(logical_expr_node={repr(self.logical_expr_node)})"
    
    def __str__(self) -> str:
        return f"{self._node_type.abbreviation}{{?{str(self.logical_expr_node)}}}/{self._node_type.abbreviation}"
    


    