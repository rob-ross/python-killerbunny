#  File: parser_nodes.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

import logging
from typing import Iterator, TYPE_CHECKING, override

from killerbunny.lexing.tokens import Token, TokenType
from killerbunny.parsing.node_type import ASTNodeType, ASTNode
from killerbunny.parsing.terminal_nodes import RootNode, CurrentNodeIdentifier
from killerbunny.shared.position import Position

if TYPE_CHECKING:
    ...
    
    
_logger = logging.getLogger(__name__)

####################################################################
# NODES
####################################################################


class SegmentNode(ASTNode):
    def __init__(self, node_type: ASTNodeType, selectors: 'RepetitionNode') -> None:
        super().__init__(node_type)
        if node_type not in (ASTNodeType.DESCENDANT_SEGMENT, ASTNodeType.CHILD_SEGMENT):
            raise ValueError(f"Expected node_type DESCENDANT_SEGMENT or CHILD_SEGMENT, but got {node_type}")
        self._selectors:RepetitionNode = selectors
    
    @property
    def selectors(self) -> 'RepetitionNode':
        return self._selectors
        
    def __repr__(self) -> str:
        repr_str = f"SegmentNode(node_type={repr(self._node_type)}, selectors={repr(self._selectors)})"
        return repr_str
    
    def __str__(self) -> str:
        node_label = self._node_type.abbreviation
        repr_str = f"{node_label}{{{self._selectors}}}/{node_label}"
        return repr_str
    
        
class BinaryOpNode(ASTNode):
    def __init__(self, left_node: ASTNode, op_token: Token, right_node: ASTNode, node_type: ASTNodeType) -> None:
        super().__init__(node_type)
        self._left_node = left_node
        self._op_token = op_token
        self._right_node = right_node
        self.set_pos(left_node._position.text, left_node._position.start, right_node._position.end)
        
    @property
    def left_node(self) -> ASTNode:
        return self._left_node
    
    @property
    def op_token(self) -> Token:
        return self._op_token
    
    @property
    def right_node(self) -> ASTNode:
        return self._right_node
        
        
    def __repr__(self) -> str:
        return (f"BinaryOpNode(left_node={repr(self._left_node)}, op_token={repr(self._op_token)}, "
                f"right_node={repr(self._right_node)}, node_type={repr(self._node_type)})")
    
    def __str__(self) -> str:
        return f"{self._node_type.abbreviation}({self._left_node}, {self._op_token.token_type.lexeme}, {self._right_node})"



class SingleNodeContainer(ASTNode):
    """Base class for containers that wrap a single ASTNode, such as UnaryOpNode.
    
    Related classes:
    BinaryOpNode is a container for two nodes:  two operands and an operator.
    RepetitionNode is a container for zero ore more nodes. The container has a type and the elements have a type.
    SingleNodeContainer is to wrap a single node. Currently its only use is as the base class of UnaryOpNode
    """
    def __init__(self, node: ASTNode, node_type: ASTNodeType) -> None:
        super().__init__(node_type)
        self._node: ASTNode = node
        
    @property
    def position(self) -> Position:
        return self._node.position
    
    @property
    def node(self) -> ASTNode:
        return self._node
    
        
    def __repr__(self) -> str:
        return f"{repr(self._node_type)}({repr(self._node)})"
    
    def __str__(self) -> str:
        return self.__str_fully_nested__()
    
    def __str_impl__(self) -> str:
        return f"{str(self._node)}"
    
    def __str_fully_nested__(self) -> str:
        """Displays info for all the nesting levels of the nodes"""
        return f"{self._node_type}({str(self._node)})"
    

class UnaryOpNode(SingleNodeContainer):
    def __init__(self, node: ASTNode, node_type: ASTNodeType, op_token: Token, ) -> None:
        """ Currently only TokenType.NOT is supported for the UnaryOpNode
        in the grammar, the only valid location for a not (!) is in front of parens, AT, or DOLLAR:
            e.g., !(@) or !($), !@, !$ ( but only in a filter selector)
            
        In other projects (not this one) this class could be used to implement pre-increment
        or pre-decrement unary op expressions, for example.
        """
        if op_token.token_type != TokenType.NOT:
            raise NotImplementedError(f"Expected TokenType.NOT. UnaryOpNode does not support {op_token.token_type}")
        super().__init__(node, node_type)
        self.op_token = op_token
        self.set_pos(op_token.position.text, op_token._position.start, node._position.end)
        
        
    def __repr__(self) -> str:
        return f"UnaryOpNode(node_type={repr(self._node_type)}, op_token={repr(self.op_token)}, node={repr(self.node)})"
        
    def __str__(self) -> str:
        return f"{self._node_type}({self.op_token.value}, {self.node})"
    

class RepetitionNode(ASTNode):
    """RepetitionNode is a list-like container for zero ore more ASTNodes.
    The container itself has a type `node_type` (implemented by the base class ASTNode),
     and  the container elements have their own type `element_type', both  expressed as an ASTNodeType.

    RepetitionNode can be used as a member of a composed class like JsonPathQueryNode, which is composed of a RootNode
    and segments implemented as a RepetitionNode.
    
    RepetitionNode can also be used by itself, and the node_type value will give its inteneded usage in AST processing.
    This prevents needing to create a separate class for every grammar production rule.
    
    see also Variable Repetition (section 3.6 in RFC 5234)
    """
    _node_list: list[ASTNode]
    _element_type: ASTNodeType
    _is_singular: bool
    def __init__(self, node_type: ASTNodeType,
                 node_list: list[ASTNode],
                 element_type: ASTNodeType,
                 is_singular: bool = False,
                 ) -> None:
        """
        
        :param node_type: Overall type for the container
        :param node_list: list of ASTNodes this container contains
        :param element_type: type of each element in the node_list
        """
        super().__init__(node_type)
        self._node_list: list[ASTNode] = node_list
        self._element_type: ASTNodeType = element_type
        self._is_singular: bool = is_singular
        if len(node_list) > 0:
            first_node = node_list[0]
            last_node = node_list[-1]
            self.set_pos(first_node.position.text, first_node.position.start, last_node.position.end)
    
    @property
    def nodes(self) -> list[ASTNode]:
        return self._node_list
        
    @property
    def element_type(self) -> ASTNodeType:
        return self._element_type
    
    
    
    def is_singular(self) -> bool:
        """Return True if this RepetitionNode represents Segments and all Segments are singular_query_segments"""
        return self._is_singular
    
        
    def __repr__(self) -> str:
        return f"RepetitionNode(node_type={repr(self._node_type)}, {repr(self._element_type)}{repr(self._node_list)})"
     
    def __str__(self) -> str:
        #return self.__str_fully_nested__()
        return self.__str_impl__()
     
    def __str_impl__(self) -> str:
        if len(self._node_list) == 0:
            return f"{self._node_type.abbreviation}[]"
        else:
            node_label = self._node_type.abbreviation
            list_str = ', '.join(str(n) for n in self._node_list)
            return f"{node_label}[{list_str}]/{node_label}"
    
    def __str_fully_nested__(self) -> str:
        """Displays info for all the nesting levels of the nodes"""
        if len(self._node_list) == 0:
            return ""
        else:
            list_str = ', '.join(str(n) for n in self._node_list)
            return f"{self._node_type}({list_str})"
    
    
    def is_empty(self) -> bool:
        return len(self._node_list) == 0
    
    ############################
    # Container Methods
    ############################
    def __len__(self) -> int:
        return len(self._node_list) if self._node_list else 0
    
    def __getitem__(self, key: int | slice) -> ASTNode | list[ASTNode] :
        """Return the element at the given index, or a slice of elements."""
        if isinstance(key, slice):
            return self._node_list[key]
        return self._node_list[key]
    
    def __iter__(self) -> Iterator[ASTNode]:
        return iter(self._node_list)
    
    def __reversed__(self) -> Iterator[ASTNode]:
        return reversed(self._node_list)
    
    def __contains__(self, item: ASTNode) -> bool:
        return item in self._node_list
    
    # --- Other useful list-like methods ---
    def append(self, item: ASTNode) -> None:
        """Append a VNode to the end of the list."""
        if not isinstance(item, ASTNode):
            raise TypeError("Can only append ASTNode instances.")
        self._node_list.append(item)
    
    def extend(self, items: 'list[ASTNode] | RepetitionNode') -> None:
        """Extend the list by appending all items from the iterable."""
        if isinstance(items, RepetitionNode):
            self._node_list.extend(items._node_list)
        elif isinstance(items, list) and all(isinstance(i, ASTNode) for i in items):
            self._node_list.extend(items)
        else:
            raise TypeError("Can only extend with a list of ASTNode or a ASTNode")
      
        
class JsonPathQueryNode(ASTNode):
    """Enclosing Node for a json_path_query. Consists of a RootNode, and zero or more segments.
    
    jsonpath_query  ::=   "$" ( segment )*
    
    """
    def __init__(self, root_node: RootNode, segments:RepetitionNode) -> None:
        if not isinstance(root_node, RootNode):
            raise TypeError(f"Expected RootNode, but got {type(root_node)}")
        if segments.node_type != ASTNodeType.SEGMENTS:
            raise TypeError(f"Expected segments.node_type to be ASTNodeType.SEGMENTS, but got {segments.node_type}")
        super().__init__(ASTNodeType.JSON_PATH_QUERY)
        self._root_node = root_node
        self._segments:RepetitionNode = segments
        self.set_pos(root_node._position.text, root_node._position.start, segments._position.end)
        
    def __repr__(self) -> str:
        return f"JsonPathQueryNode(root_node={repr(self.root_node)}, segments={repr(self.segments)})"
    
    def __str__(self) -> str:
        if len(self._segments) == 0:
            repr_str = "$"
        else:
            #join_str = f", {self.segments.node_type}<"
            join_str = f", "
            segments_str = join_str.join( str(n) for n in self.segments.nodes)
            repr_str = f"${{{segments_str}}}/$"
        return repr_str
    
    
    @property
    def root_node(self) -> RootNode:
        return self._root_node
    
    @property
    def segments(self) -> RepetitionNode:
        return self._segments
    
    @override
    def is_query(self) -> bool:
        return True
    
    @override
    def is_singular_query(self) -> bool:
        return self._segments.is_singular()
    
    
class RelativeQueryNode(ASTNode):
    """AST node for a rel_query. Encapsulates a CurrentNodeIdentifier, and zero or more segments.
    
    rel_query  ::=  "@" ( segment )*
    
    """
    def __init__(self, node: CurrentNodeIdentifier, segments:RepetitionNode) -> None:
        if not isinstance(node, CurrentNodeIdentifier):
            raise TypeError(f"Expected CurrentNodeIdentifier, but got {type(node)}")
        if segments.node_type != ASTNodeType.SEGMENTS:
            raise TypeError(f"Expected segments.node_type to be ASTNodeType.SEGMENTS, but got {segments.node_type}")
        super().__init__(ASTNodeType.REL_QUERY)
        self._current_node_identifier = node
        self._segments:RepetitionNode = segments
        self.set_pos(node._position.text, node._position.start, segments._position.end)
    
    def __repr__(self) -> str:
        return (f"RelativeQueryNode(current_node_identifier={repr(self.current_node_identifier)}, "
                f"segments={repr(self.segments)})")
    
    def __str__(self) -> str:
        if len(self.segments) == 0:
            repr_str = "@"
        else:
            join_str = f", {self.segments.node_type}<"
            segments_str = join_str.join( str(n)+'>' for n in self.segments.nodes)
            repr_str = f"@ {self.segments.node_type}<{segments_str}"
        return repr_str

    @property
    def current_node_identifier(self) -> CurrentNodeIdentifier:
        return self._current_node_identifier
    
    @property
    def segments(self) -> RepetitionNode:
        return self._segments
    
    @override
    def is_query(self) -> bool:
        return True
    
    @override
    def is_singular_query(self) -> bool:
        return self._segments.is_singular()


class RelativeSingularQueryNode(ASTNode):
    """AST node for a rel_singular_query. Encapsulates a CurrentNodeIdentifier, and zero or more segments.
    
    rel_singular_query  ::=  "@" singular_query_segments
    """
    def __init__(self, node: CurrentNodeIdentifier, segments:RepetitionNode) -> None:
        if not isinstance(node, CurrentNodeIdentifier):
            raise TypeError(f"Expected CurrentNodeIdentifier, but got {type(node)}")
        if segments.node_type != ASTNodeType.SINGULAR_QUERY_SEGMENTS:
            raise TypeError(f"Expected segments.node_type to be ASTNodeType.SINGULAR_QUERY_SEGMENTS, but got {segments.node_type}")
        super().__init__(ASTNodeType.REL_SINGULAR_QUERY)
        self._current_node_identifier = node
        self._segments:RepetitionNode = segments
        self.set_pos(node._position.text, node._position.start, segments._position.end)
    
    def __repr__(self) -> str:
        return (f"RelativeSingularQueryNode(current_node_identifier={repr(self._current_node_identifier)}, "
                f"segments={repr(self.segments)})")
    
    def __str__(self) -> str:
        if len(self.segments) == 0:
            repr_str = "@"
        else:
            node_label = self._segments.element_type.abbreviation
            join_str = f", {node_label}{{"
            segments_str = join_str.join( str(n)+'}' for n in self.segments.nodes)
            repr_str = f"@{{{node_label}{{{segments_str}}}/@"
        return repr_str
    
    @property
    def current_node_identifier(self) -> CurrentNodeIdentifier:
        return self._current_node_identifier
    
    @property
    def segments(self) -> RepetitionNode:
        return self._segments
    
    @override
    def is_query(self) -> bool:
        return True
    
    @override
    def is_singular_query(self) -> bool:
        return True
    
class AbsoluteSingularQueryNode(ASTNode):
    """AST node for an abs_singular_query. Encapsulates a RootNode, and zero or more segments.
    
    abs_singular_query  ::=  "$" singular_query_segments
    """
    def __init__(self, node: RootNode, segments:RepetitionNode) -> None:
        if not isinstance(node, RootNode):
            raise TypeError(f"Expected RootNode, but got {type(node)}")
        if segments.node_type != ASTNodeType.SINGULAR_QUERY_SEGMENTS:
            raise TypeError(f"Expected segments.node_type to be ASTNodeType.SINGULAR_QUERY_SEGMENTS, but got {segments.node_type}")
        super().__init__(ASTNodeType.ABS_SINGULAR_QUERY)
        self._root_node = node
        self._segments:RepetitionNode = segments
        self.set_pos(node._position.text, node._position.start, segments._position.end)
    
    def __repr__(self) -> str:
        return (f"AbsoluteSingularQueryNode(root_node_identifier={repr(self._root_node)}, "
                f"segments={repr(self.segments)})")
    
    def __str__(self) -> str:
        if len(self.segments) == 0:
            repr_str = "$"
        else:
            node_label = self._segments.element_type.abbreviation
            join_str = f", {node_label}{{"
            segments_str = join_str.join( str(n)+'}' for n in self.segments.nodes)
            repr_str = f"${{{node_label}{{{segments_str}}}/$"
        return repr_str
    
    @property
    def root_node(self) -> RootNode:
        return self._root_node
    
    @property
    def segments(self) -> RepetitionNode:
        return self._segments
        
        
    @override
    def is_query(self) -> bool:
        return True
    
    @override
    def is_singular_query(self) -> bool:
        return True
        