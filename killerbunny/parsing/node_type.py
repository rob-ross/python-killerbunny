#  File: node_type.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#
#

from enum import Enum

from killerbunny.shared.position import Position


class ASTNodeType(Enum):
    # value tuples are ( display name, abbreviation)
    JSON_PATH_QUERY     = "jsonpath_query"
    ROOT                = "$"
    CURRENT_NODE_ID     = "@"
    SEGMENTS            = "segments"  # ::= ( segment )*
    SEGMENT             = "segment"
    CHILD_SEGMENT       = "child_segment"      , "CS"
    DESCENDANT_SEGMENT   = "descendant_segment" , "DS"
    BRACKETED_SELECTION = "bracketed_selection", "bs"
    
    SELECTOR          = "selector"
    NAME_SELECTOR     = "name_selector"  , "ns"
    WILDCARD_SELECTOR = "wildcard"       , "*"
    INDEX_SELECTOR    = "index_selector" , "is"
    SLICE_SELECTOR    = "slice_selector" , "slice"
    FILTER_SELECTOR   = "filter_selector", "fs"
    
    LOGICAL_EXPR     = "logical_expr"
    LOGICAL_OR_EXPR  = "logical_or_expr"
    LOGICAL_AND_EXPR = "logical_and_expr"
    LOGICAL_NOT      = "logical_not"
    BASIC_EXPR       = "basic_expr"
    PAREN_EXPR       = "paren_expr"
    COMPARISON_EXPR  = "comparison_expr", "comp_expr"
    REL_QUERY        = "rel_query"
    
    REL_SINGULAR_QUERY      = "rel_singular_query"
    ABS_SINGULAR_QUERY      = "abs_singular_query"
    SINGULAR_QUERY_SEGMENTS = "singular_query_segments"
    SINGULAR_QUERY_SEGMENT  = "singular_query_segment", "sqs"
    
    
    FLOAT                 = "float"
    INT                   = "int"
    STRING                = "string"
    BOOLEAN_LITERAL       = "bool"
    NULL_LITERAL          = "null"
    IDENTIFIER            = "id"
    KEYWORD               = "keyword"
    MEMBER_NAME_SHORTHAND = "member_name_shorthand", "mns"
    
    FUNCTION              = "function",        "func"
    FUNCTION_PARAM        = "function_param",  "param"
    FUNC_PARAM_LIST       = "func_param_list", "param_list"
    FUNCTION_CALL         = "function_call",   "func()"
    FUNCTION_ARG          = "function_arg",    "arg"
    FUNC_ARG_LIST         = "func_arg_list",   "args"
    
    UNKNOWN = "unknown"
    
    def __init__(self, display_str: str, abbreviation: str = ''):
        self._display_str = display_str
        if abbreviation == '':
            self._abbreviation = display_str
        else:
            self._abbreviation = abbreviation
        
    @property
    def display_str(self) -> str:
        return self._display_str
    
    @property
    def abbreviation(self) -> str:
        return self._abbreviation
    
    def __repr__(self) -> str:
        return f"ASTNodeType.{self._display_str}"
    
    def __str__(self) -> str:
        return f"{self._display_str}"


class ASTNode:
    """ Base class for AST nodes created by the parser. """
    _position: Position
    _node_type: ASTNodeType
    def __init__(self, node_type: ASTNodeType) -> None:
        self.set_pos()
        self._node_type = node_type
        
    @property
    def position(self) -> Position:
        return self._position
    
    @property
    def node_type(self) -> ASTNodeType:
        return self._node_type
    
    def set_pos(self, text: str = '', pos_start:int = 0, pos_end: int = 0) -> 'ASTNode':
        self._position = Position(text, pos_start, pos_end)
        return self
    
    
    
    def is_query(self) -> bool:
        return False
    
    def is_singular_query(self) -> bool:
        return False
