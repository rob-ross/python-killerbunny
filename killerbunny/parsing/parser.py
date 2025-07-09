#  File: parser.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#


"""
Parses a stream of tokens and builds the AST for the evaluator.

Parser is an LL(2) recursive descent parser, although it only needs 2 token look-aheads in a handful of situations.

"""

import re
from typing import cast

from killerbunny.lexing.tokens import Token, TokenType, COMPARISON_OPERATORS_SET, \
    SEGMENT_START_TOKEN_TYPES, FILTER_QUERY_FIRST_SET, COMPARABLE_LITERAL_TYPES_SET, NUMBER_TYPES_SET, \
    JSON_KEYWORD_TOKEN_TYPES, TEST_EXPR_FIRST_SET, SINGULAR_QUERY_FIRST_SET
from killerbunny.parsing.function import get_registered_function, FunctionCallNode, FunctionNode, \
    FunctionArgument, FunctionParamType
from killerbunny.parsing.node_type import ASTNodeType, ASTNode
from killerbunny.parsing.parse_result import ParseResult
from killerbunny.parsing.parser_nodes import RepetitionNode, JsonPathQueryNode, \
    UnaryOpNode, BinaryOpNode, SegmentNode, RelativeQueryNode, RelativeSingularQueryNode, AbsoluteSingularQueryNode
from killerbunny.parsing.selector_nodes import SelectorNode, NameSelectorNode, \
    WildcardSelectorNode, SliceSelectorNode, IndexSelectorNode, FilterSelectorNode
from killerbunny.parsing.terminal_nodes import StringLiteralNode, MemberNameShorthandNode, \
    CurrentNodeIdentifier, RootNode, NumericLiteralNode, IdentifierNode, BooleanLiteralNode, \
    NullLiteralNode
from killerbunny.shared.constants import SUBPARSE_NAMES
from killerbunny.shared.errors import InvalidSyntaxError, Error, ValidationError, IllegalFunction
from killerbunny.shared.jpath_bnf import JPathBNFConstants as bnf
from killerbunny.shared.position import Position


####################################################################
# PARSER
####################################################################


class JPathParser:
    
    tokens: list[Token]
    token_index: int
    current_token: Token
    
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens: list[Token] = tokens
        self.re_init()
        
    # noinspection PyAttributeOutsideInit
    def re_init(self) -> None:
        """Reset the parser state to initial conditions. List of Tokens remains the same passed to  __init__().
        todo - add optional paramater to this method to take a new list of Tokens? Then a parser instance could
        be reused as many times as the caller needs and avoid creating a new instance each time?
        """
        self.token_index = -1
        self.current_token: Token = Token.NO_TOKEN
        self.advance()
    
    def _update_current_token(self) -> None:
        """Set the self.current_token to the token at the current self.token_index element in the `tokens` list."""
        if self.token_index < len(self.tokens):
            self.current_token =  self.tokens[self.token_index]
        else:
            self.current_token =  Token.NO_TOKEN
    
    def advance(self) -> Token:
        self.token_index += 1
        # noinspection PyUnusedLocal
        # token_debug = self.current_token
        self._update_current_token()
        #print(f"advance: {token_debug} -> {self.current_token}")
        return self.current_token
    
    
    def backtrack(self, amount: int = 1) -> Token:
        """Back up the token_index by the argumeent value."""
        self.token_index -= amount
        self._update_current_token()
        return self.current_token
    
    
    def peek_next_token(self) -> Token:
        if self.token_index + 1 < len(self.tokens):
            return self.tokens[self.token_index + 1]
        else:
            return Token.NO_TOKEN
    
    def parse(self) -> ParseResult:
        res = ParseResult()
        node = res.register(self.start())
        if res.error: return res
        return res.success(node)
    
    def start(self) -> ParseResult:
        res = ParseResult()
        if self.current_token.token_type != TokenType.DOLLAR:
            # If the query doesn't start with '$'
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected '$', got {self.current_token.token_type}"))
        # jsonpath_query will parse the '$' and all its segments.
        # It will stop when no more segments can be formed from the subsequent tokens.
        jsonpath_query_ast_node = res.register(self.jsonpath_query())
        if res.error: return res
        if jsonpath_query_ast_node is None:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected jsonpath_query, got {self.current_token.token_type}"))
        if self.current_token.token_type != TokenType.EOF:  # type: ignore
            return res.failure(
                InvalidSyntaxError(
                    self.current_token.position,
            f"Parser completed before EOF. Expected '.', '[' or '..', got {self.current_token.token_type}"))
        
        return res.success(jsonpath_query_ast_node)
    
    def subparse(self,
                 production_name: str = "all"
                 ) -> tuple[ list[ tuple[str, ASTNode] ] , list[ tuple[str, Error] ] ] :
        """Primarily a debugging method, used to parse grammar symbols other than "start". If no `prodution_name` is
        given, we try to parse all the symbol methods in the SUBPARSE_NAMES list. If a `production_name` is provided,
        we try to parse just that method. We return the result(s) of methods that don't produce a parse error.
        
        :return: a tuple of two lists. The first list contains successful parsings, the second list contains
        the Errors for unsuccessful parsings. Each list element is a 2-item tuple. The first item is the name of the
        production symbol method attempted (see SUBPARSE_NAMES).
        The second item is the ASTNode for a successful parse, (first list) or the Error
        for an unsuccessful parse (second list).
        """
        method_names: list[str] = SUBPARSE_NAMES
        
        if production_name != "all":
            method_names = [production_name]  # caller specified a particular production rule to try to parse
            
        parsing_successes: list[ tuple[str, ASTNode ]] = []
        method_errors:     list[ tuple[str, Error ]] = []
        
        for method_name in method_names:
            self.re_init()  # reset the parsing state to start of the token list
            method = getattr(self, method_name, self.no_method)
            # noinspection PyAttributeOutsideInit
            self.method_name = method_name  # this assignment is just for the error message in no_method()
            res = method()
            if not res.error and res.node and self.current_token.token_type == TokenType.EOF:
                # parsed the entire text with no errors
                parsing_successes.append( ( method_name, res.node ) )
            elif res.error:
                method_errors.append( (method_name, res.error) )
            elif res.node:
                # parsing succeeded with leftover tokens.
                #parsing_successes.append(( method_name, res.node ))
                current_token: Token = self.current_token  # parsing stopped here
                last_token = self.tokens[-1]
                error = Error(
                    Position( current_token.position.text, current_token.position.start, last_token.position.end),
                    f"{method_name}: No EOF","Parsing completed before EOF",
                )
                method_errors.append( (method_name, error) )
            
        return parsing_successes, method_errors
    
    
    def no_method(self) -> ParseResult:
        raise Exception(f"No {self.method_name} method defined")
    ####################################################################
    
    
    def jsonpath_query(self) -> ParseResult:
        """
        jsonpath_query  ::=  "$" ( segment )*
        """
        res = ParseResult()
        if self.current_token.token_type != TokenType.DOLLAR:
            return res.failure(InvalidSyntaxError(
                self.current_token.position,
                f"Expected '$', found '{self.current_token.token_type}'"))
        
        root_node_token = self.current_token
        res.register_advancement()
        self.advance() # Consume '$'
        root_node = RootNode(root_node_token)
        if self.current_token.token_type == TokenType.EOF:  # type: ignore
            # this query only consists of the root node identifier
            return res.success(JsonPathQueryNode(root_node,
                                                 RepetitionNode(ASTNodeType.SEGMENTS,
                                                                [],
                                                                ASTNodeType.SEGMENT)))
        
        segments_repetition_node = res.register(self.segments())
        if res.error: return res # Propagate error
        if segments_repetition_node is None:
            # This case should ideally be covered if segments() returns an error
            # when it can't produce a node.
            return res.failure(InvalidSyntaxError(
                self.current_token.position,
                f"Segments parsing returned no node but without an error. current token: "
                f"{self.current_token.token_type}"
            ))
        
        jsonpath_query_node = JsonPathQueryNode(root_node, cast(RepetitionNode,segments_repetition_node))
        return res.success(jsonpath_query_node)
    
    
    ####################################################################
    # SEGMENTS
    ####################################################################
    
    def segments(self) -> ParseResult:
        """Parses zero or more segment productions.
        Assumes the initial token (e.g., '$' or '@') has already been consumed.
        
        segments  ::=  ( segment )*
        
        """
        res = ParseResult()
        segments_nodes: list[ASTNode] = []
        is_singular: bool = True  # set to False at the first identification of a non-singular segment
        segment_node: SegmentNode
        while self.current_token.token_type in SEGMENT_START_TOKEN_TYPES:
            saved_token = self.current_token
            segment_node = cast(SegmentNode, res.register(self.segment())) # self.segment() will advance tokens
            if res.error:
                return res
            if segment_node is None:
                return res.failure(InvalidSyntaxError(saved_token.position,
                                            f"Expected to parse a Segment, got '{saved_token.token_type}'" ))
            
            # Determine if this segment is a Singular segment or not. We're only storing this information in the
            # returned RepititionNode for the SEGMENTS. If we need to store this in the individual segments as well,
            # we can push this code down into each self.segment() call.
            if segment_node.node_type is ASTNodeType.DESCENDANT_SEGMENT:
                is_singular = False
            # if any selectors in the segment are not INDEX_SELECTOR nor NAME_SELECTOR, it's not a singular segment
            if is_singular:  # no need to test again once we know it's not a singular segment
                if len(segment_node.selectors) > 1:
                    is_singular = False
            if is_singular:
                for selector in segment_node.selectors:
                    if not isinstance(selector, (NameSelectorNode, IndexSelectorNode)):
                        is_singular = False
                        break  # short circuit
            
            segments_nodes.append(segment_node)
        
        # Return the list of parsed segment ASTNodes directly.
        # The caller (jsonpath_query or rel_query) can modify the NodeType as needed for more specificity
        return res.success(RepetitionNode(ASTNodeType.SEGMENTS, segments_nodes, ASTNodeType.SEGMENT, is_singular))
    
    
    
    def segment(self) -> ParseResult:
        """
        segment  ::=  child_segment |
                      descendant_segment
        """
        res = ParseResult()
        if self.current_token.token_type == TokenType.DOUBLE_DOT:
            # start of descendant_segment
            descendant_segment = res.register(self.descendant_segment())
            if res.error: return res
            return res.success(descendant_segment)
        
        child_segment = res.register(self.child_segment())
        if res.error: return res
        return res.success(child_segment)
    
    def child_segment(self) -> ParseResult:
        """
        child_segment   ::=     bracketed_selection |
                                "." ( "*" | member_name_shorthand:IDENTIFIER )
        
        """
        res = ParseResult()
        if self.current_token.token_type == TokenType.LBRACKET:
            bs = res.register(self.bracketed_selection())
            if res.error: return res
            return res.success(SegmentNode(ASTNodeType.CHILD_SEGMENT, cast(RepetitionNode, bs)))
        
        if self.current_token.token_type != TokenType.DOT:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected [ or . but got {self.current_token}"))
        
        res.register_advancement()
        self.advance()  # consume '.'
        
        saved_token = self.current_token
        node: ASTNode | None = None
        if self.current_token.token_type == TokenType.STAR: # type: ignore
            wc:WildcardSelectorNode = cast(WildcardSelectorNode,res.register(self.wildcard_selector()))
            if res.error: return res
            # we want to convert a dot-wildcard into a BracketedSelectorNode ( .* ->  [*] ) for normalization
            node = self._convert_to_bracketed_selection(wc)
        elif self.current_token.token_type in  (TokenType.IDENTIFIER, *JSON_KEYWORD_TOKEN_TYPES ):
            mns:MemberNameShorthandNode = cast(MemberNameShorthandNode,res.register(self.member_name_shorthand()))
            if res.error: return res
            # convert member_name_shorthand to a bracketed name-selector ( .foo -> ["foo"] ) for normalization
            node = self._convert_to_bracketed_selection(mns)
        
        if node is not None: return res.success(SegmentNode(ASTNodeType.CHILD_SEGMENT, cast(RepetitionNode, node)))
        return res.failure(InvalidSyntaxError(self.current_token.position,
                                              f"Expected '.', '*', or identifier, but got '{saved_token.token_type}'" ))
    
    @staticmethod
    def _convert_to_bracketed_selection(node: WildcardSelectorNode | MemberNameShorthandNode) -> RepetitionNode:
        """Convert the argument ASTNode into a BracketedSelectionNode for normalization."""
        selector_list: list[SelectorNode] = []
        if isinstance(node, WildcardSelectorNode):
            selector_list.append(node)
        elif isinstance(node, MemberNameShorthandNode):
            # convert shorthand to a bracketed name-selector
            # extract the Token from the member_name_shorthand and convert it to a STRING token type
            token = node.token.copy()
            token._token_type = TokenType.STRING
            token._value = "'" + token.value + "'" # string literals are quoted, here we normalize single quotes
            new_node = NameSelectorNode(token)
            selector_list.append(new_node)
        else:
            raise TypeError(f"Unexpected ASTNode type {type(node)}")
        
        rep_node = RepetitionNode(ASTNodeType.BRACKETED_SELECTION, cast(list[ASTNode], selector_list), ASTNodeType.SELECTOR)
        return rep_node
    
    
    def descendant_segment(self) -> ParseResult:
        """
        descendant_segment  ::=  ".."  ( bracketed_selection | "*" | member_name_shorthand:IDENTIFIER )
        
        :return:
        """
        res = ParseResult()
        if self.current_token.token_type != TokenType.DOUBLE_DOT:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected .. but got {self.current_token}"))
        
        res.register_advancement()
        self.advance()
        
        if TokenType.LBRACKET == self.current_token.token_type:  # type: ignore
            bs:RepetitionNode = cast(RepetitionNode, res.register(self.bracketed_selection()))
            if res.error: return res
            if bs is not None:
                node = SegmentNode(ASTNodeType.DESCENDANT_SEGMENT, bs)
                return res.success(node)
        
        if self.current_token.token_type == TokenType.STAR: # type: ignore
            wc:WildcardSelectorNode = cast(WildcardSelectorNode,res.register(self.wildcard_selector()))
            if wc is not None:
                node = SegmentNode(ASTNodeType.DESCENDANT_SEGMENT, self._convert_to_bracketed_selection(wc))
                return res.success(node)
        
        if self.current_token.is_identifier():
            identifier:MemberNameShorthandNode = cast(MemberNameShorthandNode, res.register(self.member_name_shorthand()))
            # convert shorthand to a bracketed name-selector
            if identifier is not None:
                node = SegmentNode(ASTNodeType.DESCENDANT_SEGMENT, self._convert_to_bracketed_selection(identifier))
                return res.success(node)
                
        return res.failure(InvalidSyntaxError(self.current_token.position,
                                              f"Expected '[', '*', or identifier, got '{self.current_token.token_type }'"))
    
    
    def member_name_shorthand(self) -> ParseResult:
        """Assumes that the current token type is TokenType.IDENTIFIER.
       
        member_name_shorthand:IDENTIFIER
       
        :return:
        """
        res = ParseResult()
        if self.current_token.token_type not in (TokenType.IDENTIFIER , *JSON_KEYWORD_TOKEN_TYPES):
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected identifier, got {self.current_token.token_type}"))
        
        node = MemberNameShorthandNode(self.current_token)
        res.register_advancement()
        self.advance()
        
        return res.success(node)

    
    def bracketed_selection(self) -> ParseResult:
        """
        bracketed_selection ::= "[" selector ( "," selector)* "]"
        
        :return:
        """
        res = ParseResult()
        
        selector_list: list[ASTNode] = []
        if TokenType.LBRACKET != self.current_token.token_type:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected '[', found {self.current_token}"))
        res.register_advancement()
        self.advance()
        # must have at least one selector per the grammar
        first_selector = res.register(self.selector())
        if first_selector is None and TokenType.RBRACKET == self.current_token.token_type:  # type: ignore
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected at least one selector, got empty selector list [] "))
        elif first_selector is None :
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected at least one selector, got '{self.current_token.token_type}'"))
        selector_list.append(first_selector)
        
        # maybe more comma-delimited selectors follow
        # type ignore  is needed here because MyPy doesn't know that advance() or selector() change
        # the value of self.current_token
        while TokenType.COMMA == self.current_token.token_type:  # type: ignore
            res.register_advancement()
            self.advance()  # consume the comma
            selector_ = res.register(self.selector())
            if res.error: return res
            if selector_:
                selector_list.append(selector_)
        
        # finished with optional selectors, look for the closing ']'
        if TokenType.RBRACKET != self.current_token.token_type: # type: ignore
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected ',' or ']', found {self.current_token.token_type}"))
        res.register_advancement()
        self.advance()
        rep_node = RepetitionNode(ASTNodeType.BRACKETED_SELECTION, selector_list, ASTNodeType.SELECTOR)
        return res.success(rep_node)
    
    
    ####################################################################
    # SELECTORS
    ####################################################################
    
    
    def selector(self) -> ParseResult:
        """
        selector    ::=     name_selector:STRING_LITERAL |
                            "*" |
                            slice_selector |
                            index_selector:INT_LITERAL |
                            filter_selector
        """
        res = ParseResult()
        token = self.current_token
        node: ASTNode | None = None
        if token.token_type == TokenType.STRING:
            node = res.register(self.name_selector())
        elif token.token_type == TokenType.STAR:
            node = res.register(self.wildcard_selector())
        elif token.token_type == TokenType.SLICE:
            node = res.register(self.slice_selector())
        elif token.token_type == TokenType.INT:
            node = res.register(self.index_selector())
        elif token.token_type == TokenType.QMARK:
            node = res.register(self.filter_selector())
            
        if res.error: return res
        
        if node is not None:
            return res.success(node)
        
        else:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected selector, got '{token.token_type}'"
                                                  ))
    
    
    def name_selector(self) -> ParseResult:
        """Assumes current token is name-selector (string literal)."""
        res = ParseResult()
        if self.current_token.token_type != TokenType.STRING:
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                            f"Expected string literal, got '{self.current_token.token_type}'"))
        node = NameSelectorNode(self.current_token)
        res.register_advancement()
        self.advance()
        return res.success(node)
    
    
    def wildcard_selector(self) -> ParseResult:
        """Assumes current token is wildcard-selector (*). """
        res = ParseResult()
        if self.current_token.token_type != TokenType.STAR:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected '*', got '{self.current_token.token_type}'))"))
        node = WildcardSelectorNode(self.current_token)
        res.register_advancement()
        self.advance()
        return res.success(node)
    
    def slice_selector(self) -> ParseResult:
        """Assumes that the current token is a slice-selector. """
        res = ParseResult()
        match = re.match(bnf.SLICE_SELECTOR, self.current_token.value)
        if not match:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                            f"Expected slice-selector, got '{self.current_token.token_type}'"))
        
        start: int | None = int(match.group("start")) if match.group("start") else None
        end:   int | None = int(match.group("end"))   if match.group("end")   else None
        step:  int | None = int(match.group("step"))  if match.group("step")  else None
        try:
            node = SliceSelectorNode(self.current_token, start, end, step)
        except IndexError as ie:
            return res.failure(ValidationError(self.current_token.position, str(ie) ))
        res.register_advancement()
        self.advance()
        return res.success(node)
    
    
    def index_selector(self) -> ParseResult:
        """
        Assumes current token is index selector (int literal).
        
        index_selector:INT_LITERAL
        
        :return:
        """
        res = ParseResult()
        if self.current_token.token_type != TokenType.INT:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                        f"Expected int literal, got '{self.current_token.token_type}'"))
        node = IndexSelectorNode(self.current_token)
        res.register_advancement()
        self.advance()
        return  res.success(node)
    
    
    def filter_selector(self) -> ParseResult:
        """Assumes current token is question mark (?).
        
        filter_selector  ::=  "?" logical_expr
        
        :return:
        """
        res = ParseResult()
        if self.current_token.token_type != TokenType.QMARK:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected '?', got {self.current_token.token_type}"))
        res.register_advancement()
        self.advance()
        
        node = res.register(self.logical_expr())
        if res.error: return res
        
        if node is None:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected logical_expr, got {self.current_token.token_type}"))
        
        return res.success(FilterSelectorNode(node))
        
    
    ####################################################################
    # LOGICAL EXPR
    ####################################################################
    
    def logical_expr(self) -> ParseResult:
        """
        
        logical_expr  ::= logical_or_expr
        
        """
        res = ParseResult()
        logexpr_node = res.register(self.logical_or_expr())
        if res.error: return res
        if logexpr_node is None:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected logical_or_expr, got {self.current_token.token_type}"))
                
        return res.success(logexpr_node)
    
    def logical_or_expr(self) -> ParseResult:
        """
        Disjunction binds less tightly than conjuntion
        
        logical_or_expr  ::=  logical_and_expression ( "||" logical_and_expression )*
        
        :return:
        """
        """
        Implementation detail:
            We use a list for the concatenated logical_and_expressions instead of nested nodes so that we can use
            short-circuit logic at the top level. If any list members evaluate to True,
            the entire logical_or_expr is True.
        """
        res = ParseResult()
        and_expr_list: list[ASTNode] = []
        node = res.register(self.logical_and_expr())
        if res.error: return res
        if node is None:
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                                   f"Expected logical_and_expr, got {self.current_token.token_type}" ))
        and_expr_list.append(node)
        
        # maybe more '||'-delimited logical_and_expressions follow
        while TokenType.OR == self.current_token.token_type:
            res.register_advancement()
            self.advance()  # consume the '||'
            node = res.register(self.logical_and_expr())
            if res.error: return res
            if node is None:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_token.position,
                        f"Expected logical_and_expr after '||', got {self.current_token.token_type}"
                    ))
            and_expr_list.append(node)
        
        if len(and_expr_list) == 1:
            # no need to wrap this single node in a RepetitionNode
            logical_or_expr_node = and_expr_list[0]
        else:
            logical_or_expr_node = RepetitionNode(ASTNodeType.LOGICAL_OR_EXPR, and_expr_list, ASTNodeType.LOGICAL_AND_EXPR)
        return res.success(logical_or_expr_node)
        #return res.success(SingleNodeContainer(log_and_exprs, NodeType.LOGICAL_OR_EXPR))
    
    def logical_and_expr(self) -> ParseResult:
        """
        conjunction, binds more tightly than disjunction
        
        logical_and_expr  ::=  basic_expr ( "&&" basic_expr )*
        
        :return:
        """
        
        """
        Implementation detail:
            We use a list for the concatenated basic_exprs instead of nested Nodes so that we can use short-circuit logic
            at the top level. If any list members evaluate to False, the entire logical_and_expr is False.
        """
        # todo this concatenation pattern has appeared several times now. perhaps refactor to a common method:
        #   concat_production(token_type, prod_func, error_msg)
        res = ParseResult()
        basic_expr_list: list[ASTNode] = []
        node = res.register(self.basic_expr())
        if res.error: return res
        if node is None:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected basic_expr, got {self.current_token.token_type}"))
        basic_expr_list.append(node)
        # maybe more '&&'-delimited logical_and_expressions follow
        while TokenType.AND == self.current_token.token_type:
            res.register_advancement()
            self.advance()  # consume the '&&'
            node = res.register(self.basic_expr())
            if res.error: return res
            if node is None:
                return res.failure(
                    InvalidSyntaxError(self.current_token.position,
                                       f"Expected basic_expr after '&&', got {self.current_token.token_type}"))
            else:
                basic_expr_list.append(node)
        
        if len(basic_expr_list) == 1:
            # no need to wrap this single node in a RepetitionNode
            basic_exprs = basic_expr_list[0]
        else:
            basic_exprs = RepetitionNode(ASTNodeType.LOGICAL_AND_EXPR, basic_expr_list, ASTNodeType.BASIC_EXPR)
        # return res.success(SingleNodeContainer(basic_exprs, NodeType.LOGICAL_AND_EXPR))
        return res.success(basic_exprs)
    
    def basic_expr(self) -> ParseResult:
        """
        
        basic_expr ::= paren_expr | comparison_expr | test_expr
        
        :return:
        """
        res = ParseResult()
        if self.current_token.token_type == TokenType.NOT:
            # the next symbol is either paren_expr or test_expr
            if self.peek_next_token().token_type == TokenType.LPAREN:
                node = res.register(self.paren_expr())
                if res.error: return res
                return res.success(node)
            else:
                node = res.register(self.test_expr())
                if res.error: return res
                return res.success(node)

        # no not symbol ( ! ), which means it could be any of the three (paren_expr, comparison_expr, test_expr)
        token_type = self.current_token.token_type
        if token_type == TokenType.LPAREN:
            node = res.register(self.paren_expr())
            if res.error: return res
            return res.success(node)
        
        # try parsing comparison_expr
        # if parsing comparison_expr() fails, we need to reset the token index to its value at this point so we can
        # try parsing test_expr next
        node = res.try_register(self.comparison_expr())
    
        if res.error is None and node is not None:
            return res.success(node)
        
        # If the comparison_expr failed, it may just mean it wasn't a comparison_expr. We'll clear the error so we can
        # try to parse a test_expr(). If that fails too it's ambiguous as to which production was intended.
        self.backtrack(res.to_reverse_count)
        res.error = None

        if self.current_token.token_type in TEST_EXPR_FIRST_SET or self.is_start_of_function_expr():
            # if the token_type is IDENTIFIER followed by LPAREN, we have basic_expr -> test_expr -> function_expr
            # otherwise the identifier might just be a member-name-shorthand or JSON keyword like true, false, null
            node = res.register(self.test_expr())
            if res.error: return res
            if node is not None:
                return res.success(node)
                

        """
        first set for comparison_expr:
        
        comparison_expr  ::=  comparable ( "=="  |  "!="  |  "<="  |  ">="  |  "<"  |  ">")  comparable
        
        comparable  ::=  singular_query |    ; singular query value
                         function_expr  |    ; ValueType
                         literal
                         
        singluar_query          ::=     rel_singular_query | abs_singluar_query
        function_expr           ::=     function_name:IDENTIFIER "(" [ function_argument ( "," function_argument )* ] ")"
        rel_singular_query      ::=     "@" singular_query_segments
        abs_singular_query      ::=     "$" singular_query_segments

        literal
        IDENTIFIER
        @
        $
        """

        """"
        first set for test_expr:
        test_expr               ::=     [ "!" ] ( filter_query | function_expr )
        
        filter_query            ::=     rel_query | jsonpath_query
        function_expr           ::=     function_name:IDENTIFIER "(" [ function_argument ( "," function_argument )* ] ")"
        
        rel_query               ::=     "@" segments
        jsonpath_query          ::=     "$" segments
        
        function_name:IDENTIFIER (
        "@" segments
        "$" segments
        """

        
        return res.failure(
            InvalidSyntaxError(self.current_token.position,
                    f"Expected paren_expr, comparison_expr or test_expr, got {self.current_token.token_type}"))
    
    
    def paren_expr(self) -> ParseResult:
        """
        paren_expr  ::=  [ "!" ] "(" logical_expr ")"
        
        :return:
        """
        res = ParseResult()
        # we can store the optional "not" operator in the ParenExprNode, which will negate the entire nested logical_expr
        # or have a NotOpNode that takes one nested ASTNode of ParenExprNode | TestExprNode
        not_flag = False
        not_token = self.current_token
        if self.current_token.token_type == TokenType.NOT:
            not_flag = True
            res.register_advancement()
            self.advance()
        
        
        logical_expr_node: ASTNode | None
        if self.current_token.token_type != TokenType.LPAREN:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                           f"Expected '(', got {self.current_token.token_type}"))
        res.register_advancement()
        self.advance()
        logical_expr_node = res.register(self.logical_expr())
        if res.error: return res
        if logical_expr_node is None:
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                        f"logical_expr_node is None, current token: {self.current_token.token_type}"
            ))
        if self.current_token.token_type != TokenType.RPAREN:  # type: ignore
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                           f"Expected ')', got {self.current_token.token_type}"))
        res.register_advancement()
        self.advance()
        
        inner_node: ASTNode
        if not_flag:
            result_node = UnaryOpNode(logical_expr_node, ASTNodeType.LOGICAL_NOT, not_token)
        else:
            result_node = logical_expr_node
            
        # result_node = SingleNodeContainer(inner_node, ASTNodeType.PAREN_EXPR)
        
        return res.success(result_node)
    
    
    def comparison_expr(self) -> ParseResult:
        """
        comparison_expr  ::=  comparable ( "=="  |  "!="  |  "<="  |  ">="  |  "<"  |  ">")  comparable
        
        :return:
        """
        res = ParseResult()
        left_node = res.register(self.comparable())
        if res.error: return res
        if left_node is None:
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                        f"Comparison_expr: couldn't parse left comparable, current token: {self.current_token.token_type}"))

        
        if self.current_token.token_type not in COMPARISON_OPERATORS_SET:
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                    f"Expected '==', '!=', '<=', '>=', '<', '>', got {self.current_token.token_type}"))

        
        op_token: Token = self.current_token
        res.register_advancement()
        self.advance()
        right_node = res.register(self.comparable())
        if res.error: return res
        if right_node is None:
            return res.failure(
                InvalidSyntaxError(
                self.current_token.position,
        f"Comparison_expr: couldn't parse right comparable, current token: {self.current_token.token_type}"
            ))
        
        # todo if one or both of the comparables are function_expr, check that they are well typed
        
        node = BinaryOpNode(left_node, op_token, right_node, ASTNodeType.COMPARISON_EXPR)
        return res.success(node)
    
    
    def test_expr(self) -> ParseResult:
        """
        
        test_expr  ::=  [ "!" ] ( filter_query | function_expr )
        
        :return:
        """
        res = ParseResult()
        
        not_flag = False
        not_token = self.current_token
        if self.current_token.token_type == TokenType.NOT:
            not_flag = True
            self.advance()
        node: ASTNode | None = None
        if self.current_token.token_type in FILTER_QUERY_FIRST_SET:
            node = res.register(self.filter_query())
        elif self.is_start_of_function_expr():
            node = res.register(self.function_expr())
            # well-typedness check
            if res.error is None and node is not None:
                """pg 36 RFC 9535: For a function expression to be well-typed:
                    1. Its declared type must be well-typed in the context in which it occurs.
                        As a test-expr in a logical expression:
                            The function's declared result type is LogicalType or (giving rise to conversion
                            as per Section 2.4.2) NodesType.
                """
                func_expr = cast(FunctionCallNode, node)
                func_type = func_expr.func_node.func_type
                if func_type not in ( FunctionParamType.LogicalType, FunctionParamType.NodesType):
                    msg = f"Function not well-typed for test_expr. Expected LogicalType or NodesType, got {func_type}"
                    return res.failure(ValidationError(func_expr.position, msg))
            
        if res.error: return res
        if node is not None:
            if not_flag:
                not_node = UnaryOpNode(node, ASTNodeType.LOGICAL_NOT, not_token)
                return res.success(not_node)
            else:
                return res.success(node)
            
        return res.failure(
            InvalidSyntaxError(self.current_token.position,
                               f"Expected filter_query or function_expr, got {self.current_token.token_type}"))
    
    
    def filter_query(self) -> ParseResult:
        """
        
        filter_query  ::=  rel_query | jsonpath_query
        
        :return:
        """
        res = ParseResult()
        if self.current_token.token_type not in FILTER_QUERY_FIRST_SET:
            # If current token is neither '@' nor '$', it's not a valid start for a filter_query
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                                   f"Expected '@' or '$', got {self.current_token.token_type}"))
        
        if self.current_token.token_type == TokenType.AT:
            # If it starts with '@', attempt to parse as rel_query
            node = res.register(self.rel_query())
        else:
            # If it starts with '$', attempt to parse as jsonpath_query
            node = res.register(self.jsonpath_query())
            
        if res.error: return res
        return res.success(node)
    
    
    def rel_query(self) -> ParseResult:
        """
        rel_query  ::=  "@" ( segment )*
        
        rel_query is part of test_expr, testing the existence of an element as a filter for including the current node
        :return:
        """
        res = ParseResult()
        
        if self.current_token.token_type != TokenType.AT:
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                                   f"Expected '@', got {self.current_token.token_type}"))
        
        at_token = self.current_token # Save for potential AST node construction
        res.register_advancement()
        self.advance()  # consume the @ token
        
        segments_node = res.register(self.segments())
        if res.error: return res

        cur_node_id = CurrentNodeIdentifier(at_token)
        rel_query_node = RelativeQueryNode(cur_node_id, cast(RepetitionNode, segments_node))
        rel_query_node.set_pos(at_token.position.text, at_token.position.start, self.current_token.position.start)
        return res.success(rel_query_node)
    
    
    def comparable(self) -> ParseResult:
        """
        
        comparable  ::=  singular_query |    ; singular query value
                         function_expr  |    ; ValueType
                         literal
                         
        :return: the parsed comparable ASTNode in ParseResult.node
        """
        res = ParseResult()
        node: ASTNode | None = None
        if self.current_token.token_type in SINGULAR_QUERY_FIRST_SET:
            node = res.register(self.singular_query())
            if res.error: return res
            if node is not None:
                return res.success(node)
            else:
                return res.failure(
                    InvalidSyntaxError(self.current_token.position,
                                f"Expected singular_query, got {self.current_token.token_type}"))
        
        elif self.is_start_of_function_expr():
            node = res.register(self.function_expr())
            if res.error: return res
            if node is not None:
                """see pg 36 in RFC 9535
                For a function expression to be well-typed:
                    1. Its declared type must be well-typed in the context in which it occurs.
                        As a comparable in a comparison:
                        The function's declared result type is ValueType.
                """
                func_expr = cast(FunctionCallNode, node)
                func_type = func_expr.func_node.func_type
                if func_type != FunctionParamType.ValueType:
                    msg = f"Function not well-typed for test_expr. Expected ValueType, got {func_type}"
                    return res.failure(ValidationError(func_expr.position, msg))
                
                return res.success(node)
            else:
                return res.failure(
                    InvalidSyntaxError(self.current_token.position,
                                       f"Expected function_expr, got {self.current_token.token_type}")
                )
        
        # literals
        elif self.current_token.token_type in COMPARABLE_LITERAL_TYPES_SET:
            match self.current_token.token_type:
                case TokenType.STRING:
                    node = res.register(self.string_literal())
                case TokenType.INT | TokenType.FLOAT:
                    node = res.register(self.number_literal())
                case TokenType.TRUE | TokenType.FALSE | TokenType.NULL:
                    node = res.register(self.json_keyword())
            if res.error: return res
            if node is not None:
                return res.success(node)
            else:
                return res.failure(
                    InvalidSyntaxError(self.current_token.position,
                f"Expected literal int, float, str, true, false, or null, got {self.current_token.token_type}")
                )
        

        return res.failure(
            InvalidSyntaxError(self.current_token.position,
                    f"Expected singular_query, function_expr, or literal, got {self.current_token.token_type}")
        )
    
    def singular_query(self) -> ParseResult:
        """
        singluar_query  ::=  rel_singular_query | abs_singluar_query

        :return:
        """
        res = ParseResult()
        if self.current_token.token_type not in SINGULAR_QUERY_FIRST_SET:
            return res.failure(
                InvalidSyntaxError(
                    self.current_token.position,
                    f"Expected '@' or '$', got {self.current_token.token_type}")
            )
        
        node: ASTNode | None = None
        match self.current_token.token_type:
            case TokenType.AT:
                node = res.register(self.rel_singular_query())
            case TokenType.DOLLAR:
                node = res.register(self.abs_singular_query())
        
        if res.error: return res
        if node is None:
            return res.failure(
                InvalidSyntaxError(
                    self.current_token.position,
                    f"Expected rel_singular_query or abs_singular_query, got {self.current_token.token_type}"
            ))
        
        return res.success(node)
        
    
    def rel_singular_query(self) -> ParseResult:
        """
        rel_singular_query      ::=     "@" singular_query_segments

        :return:
        
        """
        res = ParseResult()
        if self.current_token.token_type != TokenType.AT:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected '@', got {self.current_token.token_type}"))
        at_token = self.current_token
        res.register_advancement()
        self.advance()
        
        
        segments = res.register(self.singular_query_segments())
        if res.error: return res
        if segments is None:
            return res.failure(InvalidSyntaxError(
                self.current_token.position,f"Expected '[' or '.', got {self.current_token.token_type}"))
            
        cur_node_id = CurrentNodeIdentifier(at_token)
        rel_single_query_node = RelativeSingularQueryNode(cur_node_id, cast(RepetitionNode, segments))
        return res.success(rel_single_query_node)
    
    
    def abs_singular_query(self) -> ParseResult:
        """
        abs_singular_query  ::= "$" singular_query_segments

        :return:
        """
        res = ParseResult()
        if self.current_token.token_type != TokenType.DOLLAR:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected '$', got {self.current_token.token_type}"))
        dollar_token = self.current_token
        res.register_advancement()
        self.advance()
        
        segments = res.register(self.singular_query_segments())
        if res.error: return res
        if segments is None:
            return res.failure(InvalidSyntaxError(
                self.current_token.position,f"Expected '[' or '.', got {self.current_token.token_type}"))
        
        root_node = RootNode(dollar_token)
        rel_single_query_node = AbsoluteSingularQueryNode(root_node, cast(RepetitionNode, segments))
        
        return res.success(rel_single_query_node)
        
    
    def singular_query_segments(self) -> ParseResult:
        """
        Parse zero or more segments of name_segment or index_segment. Wrap returned segments in a RepetitionNode
        
        singular_query_segments ::=  ( singular_query_segment )*

        :return:
        """
        res = ParseResult()
        segments: list[SelectorNode] = []
        while self.current_token.token_type in (TokenType.LBRACKET, TokenType.DOT ):
            segment_node = res.register(self.singular_query_segment())
            
            if res.error: return res
            if segment_node is None:
                return res.failure(InvalidSyntaxError(self.current_token.position,
                                f"Expected singular_query_segment, got {self.current_token.token_type}"))
            segments.append(cast(SelectorNode, segment_node))
            

        result_node = RepetitionNode( ASTNodeType.SINGULAR_QUERY_SEGMENTS,
                                      cast(list[ASTNode], segments) ,
                                      ASTNodeType.SINGULAR_QUERY_SEGMENT )
        return res.success(result_node)
    
    
    def singular_query_segment(self) -> ParseResult:
        """
        
        singular_query_segment ::=  name_segment | index_segment
        
        :return: NamesSelectorNode or IndexSelectorNode in ParseResult.node
        """
        res = ParseResult()
        if self.current_token.token_type not in (TokenType.LBRACKET, TokenType.DOT ):
            return res.failure(InvalidSyntaxError(
                self.current_token.position, f"Expected '[' or '.', got {self.current_token.token_type}"
            ))
        
        node: ASTNode | None
        if self.current_token.token_type == TokenType.DOT:
            saved_token = self.current_token
            node = res.register(self.name_segment())
            if res.error: return res
            if node is None:
                return res.failure(InvalidSyntaxError(self.current_token.position,
                                                      f"Expected name_segment, got {saved_token.token_type}"))
            return res.success(node)
        
        if self.current_token.token_type == TokenType.LBRACKET:
            next_token = self.peek_next_token()
            saved_token = self.current_token
            if next_token.token_type == TokenType.INT:
                node = res.register(self.index_segment())
                if res.error: return res
                if node is None:
                    return res.failure(InvalidSyntaxError(saved_token.position,
                                                          f"Expected index_segment, got {saved_token.token_type}"))
                return res.success(node)
            elif next_token.token_type == TokenType.STRING:
                node = res.register(self.name_segment())
                if res.error: return res
                if node is None:
                    return res.failure(InvalidSyntaxError(saved_token.position,
                                                          f"Expected name_segment, got {saved_token.token_type}"))
                return res.success(node)
            
        return res.failure(InvalidSyntaxError(self.current_token.position,
                                f"Expected name_segment or index_segment, got {self.current_token.token_type}"))
        
            
            
            
    
    def name_segment(self) -> ParseResult:
        """
        
        name_segment ::=  ( "[" name_selector:STRING_LITERAL "]" ) | ( "." member_name_shorthand:IDENTIFIER )

        :return: A NameSelectorNode in ParseResult.node. Converts a member_name_shorthand to NameSelectorNode.
        """
        res = ParseResult()
        
        if self.current_token.token_type not in (TokenType.LBRACKET, TokenType.DOT):
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                        f"Expected '[' or '.', got {self.current_token.token_type}"))
        # parse string literal
        if self.current_token.token_type == TokenType.LBRACKET:
            res.register_advancement()
            self.advance()
            saved_token = self.current_token
            node = res.register(self.name_selector())
            if res.error: return res
            if node is None:
                return res.failure(InvalidSyntaxError(self.current_token.position,
                                                f"Expected name_selector, got {saved_token.token_type}'",
                ))
            
            if self.current_token.token_type  != TokenType.RBRACKET:  # type: ignore
                return res.failure(InvalidSyntaxError(self.current_token.position,
                                                      f"Expected ']', got {self.current_token.token_type}"))
            res.register_advancement()
            self.advance()
            return res.success(node)
        
        # parse member_name_shorthand
        elif self.current_token.token_type == TokenType.DOT:
            res.register_advancement()
            self.advance() # consume .
            if not self.current_token.is_identifier():
                return res.failure(InvalidSyntaxError(self.current_token.position,
                                                f"Expected identifier, got {self.current_token.token_type}"))
            saved_token = self.current_token
            node = res.register(self.member_name_shorthand())
            if res.error: return res
            if node is None:
                return res.failure(InvalidSyntaxError(self.current_token.position,
                                            f"Expected member_name_shorthand, got {saved_token.token_type}"))
            # convert MemberNameShorthandNode to a NameSelectorNode
            # extract the Token from the member_name_shorthand and convert it to a STRING token type
            mns_node: MemberNameShorthandNode = cast(MemberNameShorthandNode, node)
            
            token = mns_node.token.copy()
            token._token_type = TokenType.STRING
            token._value = "'" + token.value + "'" # string literals are quoted, here we normalize single quotes
            new_node = NameSelectorNode(token)
            return res.success(new_node)
    
        return res.failure(InvalidSyntaxError(self.current_token.position,
                    f"Expected name_selector or member_name_selector, got {self.current_token.token_type}"))
    
    def index_segment(self) -> ParseResult:
        """
        
        index_segment  ::=  "[" index_selector:INT_LITERAL "]"

        :return:  IndexSelectorNode for the int literal token
        """
        res = ParseResult()
        if self.current_token.token_type != TokenType.LBRACKET:
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                            f"Expected '[', got {self.current_token.token_type}"))
    
        res.register_advancement()
        self.advance()  # consume '['
        
        if self.current_token.token_type != TokenType.INT:  # type: ignore
            return res.failure(InvalidSyntaxError(
                self.current_token.position,
                f"Expected int literal, got {self.current_token.token_type}"))
        
        saved_token = self.current_token
        node = res.register( self.index_selector())
        if res.error: return res
        if node is None:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected index_selector, got {saved_token.token_type}"))
        
        if self.current_token.token_type != TokenType.RBRACKET:
            return res.failure(
                InvalidSyntaxError(self.current_token.position,
                                   f"Expected ']', got {self.current_token.token_type}"))
        
        res.register_advancement()
        self.advance()  # consume ']'
        
        return res.success(node)

    FUNCTION_NAME_RE = re.compile(bnf.FUNCTION_NAME)
    
    def  function_expr(self) -> ParseResult:
        """
        
        function_expr  ::=  function_name:IDENTIFIER "(" [ function_argument ( "," function_argument )* ] ")"

        :return: FunctionCallNode in ParseResult.node if successful
        """
        res = ParseResult()
        if not self.current_token.is_identifier():
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                           f"Expected function_name, got {self.current_token.token_type}"))
        function_name = self.current_token
        if not JPathParser.FUNCTION_NAME_RE.match(function_name.value):
            return res.failure(IllegalFunction(function_name.position,
                                               f"Function name '{function_name.value}' is not well-formed"))
        
        # does the function exist?
        function: FunctionNode | None = get_registered_function(function_name.value)
        if function is None:
            return res.failure(IllegalFunction(self.current_token.position,
                                               f"Function name '{function_name.value}' is not registered"))
        res.register_advancement()
        self.advance()  # consume function name
        
        if self.current_token.token_type != TokenType.LPAREN:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected '(', got {self.current_token.token_type}"))
        res.register_advancement()
        self.advance()  # consume '('
        
        first_arg_token: Token = self.current_token
        if self.current_token.token_type == TokenType.RPAREN:  # type: ignore
            # no function_argument list
            res.register_advancement()
            self.advance()  # consume `)` after an empty arg list
            try:
                fcn = FunctionCallNode(
                        function,
                        RepetitionNode(ASTNodeType.FUNC_ARG_LIST, [], ASTNodeType.FUNCTION_ARG)
                    )
            except re.error as e:
                return res.failure(ValidationError(first_arg_token.position.copy(), str(e)))
            
            fcn.set_pos(function_name.position.text, function_name.position.start, self.current_token.position.start)
            return res.success(fcn)
            
        # At this point, we know we have at least one function call argument
        arg_index: int = 0
        arg_list: list[FunctionArgument] = []
        saved_token = self.current_token
        func_params = function.param_list
        func_arg: FunctionArgument
        func_arg = cast(FunctionArgument,res.register( self.function_argument() ))
        if res.error: return res
        if func_arg is None:
            return res.failure(
                InvalidSyntaxError(saved_token.position,
                                        f"Expected function argument, got {saved_token.token_type}"))
                
        if len(func_params) == 0:
            # this function argument is extraneous as the function takes no parameters
            return res.failure(
                InvalidSyntaxError(func_arg.position,
                                   f"Unexpected function argument for no-param function, got {func_arg}"))
        
        try:
            func_arg.validate_type(func_params[arg_index])
        except TypeError as te:
            return res.failure( ValidationError(func_arg.position, str(te) ))
            
        arg_list.append(func_arg)

        
        # optional arguments
        #   parse comma then argument.
        while self.current_token.token_type == TokenType.COMMA:  # type: ignore
            arg_index += 1
            res.register_advancement()
            self.advance()
            saved_token = self.current_token
            func_arg = cast(FunctionArgument, res.register( self.function_argument() ))
            if res.error: return res
            if func_arg is None:
                return res.failure(
                    InvalidSyntaxError(saved_token.position,
                                       f"Expected function argument, got {saved_token.token_type}"))
                        
            if arg_index >= len(func_params):
                # this function argument is extraneous
                s_or_blank = '' if len(func_params) == 1 else 's'
                return res.failure(
                    ValidationError(func_arg.position,
                    f"Unexpected function argument for function with only {len(func_params)} parameter{s_or_blank}"))
        
            try:
                func_arg.validate_type(func_params[arg_index])
            except TypeError as te:
                return res.failure( ValidationError(func_arg.position, str(te) ))
            
            arg_list.append(func_arg)

            
        if arg_index + 1 < len(func_params)  :
            # not enough arguments for this function
            return res.failure(
                ValidationError(self.current_token.position,
                                f"Expected {len(func_params)} arguments for function, got {arg_index + 1}"))
        
        if self.current_token.token_type != TokenType.RPAREN:  # type: ignore
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected ')', got {self.current_token.token_type}"))
        saved_token = self.current_token
        res.register_advancement()
        self.advance()  # consume ')' after the argument list
        
        try:
            fcn = FunctionCallNode( function,
                              RepetitionNode(ASTNodeType.FUNC_ARG_LIST, arg_list, ASTNodeType.FUNCTION_ARG)
            )
        except re.error as e:
            err_pos = Position(first_arg_token.position.text,first_arg_token.position.start, saved_token.position.start)
            return res.failure(ValidationError(err_pos, str(e)))
            
        fcn.set_pos(function_name.position.text, function_name.position.start, self.current_token.position.start)
        return res.success(fcn)
    

    
    def function_argument(self) -> ParseResult:
        """
        function_argument  ::=  logical_expr  |
                                filter_query  |  ; includes singular query
                                function_expr |
                                literal
        :return:
        """
        res = ParseResult()
        
        if self.current_token.token_type in FILTER_QUERY_FIRST_SET:
            # parse as filter query
            saved_token = self.current_token
            fq_node = res.register(self.filter_query())
            if res.error: return res
            if fq_node is None:
                return res.failure(InvalidSyntaxError(saved_token.position,
                                              f"Expected filter_quer, got {saved_token.token_type}"))
            fa = FunctionArgument(fq_node)
            fa.set_pos(saved_token.position.text, saved_token.position.start, self.current_token.position.start)
            return res.success( fa )
        
        if self.is_start_of_function_expr():
            saved_token = self.current_token
            func_expr = res.register(self.function_expr())
            if res.error: return res
            if func_expr is None:
                return res.failure(InvalidSyntaxError(saved_token.position,
                                                      f"Expected function_expr, got {saved_token.token_type}"))
                
            fa = FunctionArgument(func_expr)
            fa.set_pos(saved_token.position.text, saved_token.position.start, self.current_token.position.start)
            return res.success(fa)
        
        # Try parsing as logical_expr. If returns none or error, backtrack and then try literal
        saved_token = self.current_token
        logical_expr = res.try_register(self.logical_expr())
        if res.error or logical_expr is None:
            self.backtrack(res.to_reverse_count)
        else:
            fa = FunctionArgument(logical_expr)
            fa.set_pos(saved_token.position.text, saved_token.position.start, self.current_token.position.start)
            return res.success(fa)
        
        # literal or error
        saved_token = self.current_token
        if self.current_token.token_type in COMPARABLE_LITERAL_TYPES_SET:
            token_type = self.current_token.token_type
            literal_node = None
            if token_type == TokenType.STRING:
                literal_node = res.register(self.string_literal())
            elif token_type in NUMBER_TYPES_SET:
                literal_node = res.register(self.number_literal())
            elif token_type in JSON_KEYWORD_TOKEN_TYPES:
                literal_node = res.register(self.json_keyword())
            if res.error: return res
            if literal_node is None:
                return res.failure(InvalidSyntaxError(saved_token.position,
                                                      f"Couldn't parse literal token {token_type}"))
            fa = FunctionArgument(literal_node)
            fa.set_pos(saved_token.position.text, saved_token.position.start, self.current_token.position.start)
            return res.success(fa)
            
        return res.failure(InvalidSyntaxError(saved_token.position,
                                        f"Expected to parse function argument, got {saved_token.token_type}"))
    
    
    ############################################################################
    
    
    def is_start_of_function_expr(self) -> bool:
        if self.current_token.is_identifier() and self.peek_next_token().token_type == TokenType.LPAREN:
            return True
        return False
    
    
    def identifier(self) -> ParseResult:
        res = ParseResult()
        if not self.current_token.is_identifier():
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected identifier, got {self.current_token.token_type}"))
        node = IdentifierNode(self.current_token)
        res.register_advancement()
        self.advance()
        return res.success(node)
    
    
    def json_keyword(self) -> ParseResult:
        """Parse JSON keywords true, false, and null and create literal nodes for them."""
        res = ParseResult()
        if self.current_token.token_type not in JSON_KEYWORD_TOKEN_TYPES:
            return res.failure(  InvalidSyntaxError(self.current_token.position,
                        f"Expected keyword 'true', 'false', or 'null', got {self.current_token.token_type}"))
        
        node: ASTNode
        match self.current_token.token_type:
            case TokenType.TRUE | TokenType.FALSE:
                node = BooleanLiteralNode(self.current_token)
            case TokenType.NULL:
                node = NullLiteralNode(self.current_token)
        
        res.register_advancement()
        self.advance()
        # noinspection PyUnboundLocalVariable
        return res.success(node)  # node cannot be none here
    
    
    def number_literal(self) -> ParseResult:
        res = ParseResult()
        if self.current_token.token_type not in NUMBER_TYPES_SET:
            res.failure(InvalidSyntaxError(self.current_token.position,
                                        f"Expected int or float literal, got {self.current_token.token_type}"))
        node = NumericLiteralNode(self.current_token)
        res.register_advancement()
        self.advance()
        return res.success(node)
    
    
    def string_literal(self) -> ParseResult:
        """
        Assumes the current token is string literal.
        
        Included for completeness. Not currently used, as the only production that uses a string literal
        is name-selector, and that processes the string-literal directly.
        
        string_literal:STRING_LITERAL
        
        :return: A new StringLiteralNode in ParseResult.node
        """
        res = ParseResult()
        if self.current_token.token_type != TokenType.STRING:
            return res.failure(InvalidSyntaxError(self.current_token.position,
                                                  f"Expected string literal, got {self.current_token.token_type}"))
        node = StringLiteralNode(self.current_token)
        res.register_advancement()
        self.advance()
        return res.success(node)

