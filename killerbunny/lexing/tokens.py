#  File: tokens.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#
#

from enum import Enum

from killerbunny.shared.position import Position
from killerbunny.shared.jpath_bnf import JPathBNFConstants as bnf


####################################################################
# LEXER / PARSER TOKENS (non AST)
####################################################################


class TokenCategory(Enum):
    # Base token types
    LITERAL = "LITERAL"
    KEYWORD = "KEYWORD"
    COMPARISON_OPERATOR = "COMPARISON_OPERATOR"
    LOGICAL_OPERATOR = "LOGICAL_OPERATOR"
    DELIMITER = "DELIMITER"
    
    IDENTIFIER = "IDENTIFIER"
    # special
    NO_OP   = "NO_OP"
    UNKNOWN = "UNKNOWN"
    EOF     = "EOF"
    
    def __repr__(self) -> str:
        return f"TokenCategory(name={repr(self.name)})"


class TokenType(Enum):
    """`lexeme` is the literal char(s) that represent this token type. E.g., '$' or '<='. For most token types we use
    this value to match the input stream in the lexer. This value is also used to lookup the token type
    in TOKEN_LOOKUP_DICT. For SPACE, INT, FLOAT, STRING, SLICE, and IDENTIFIER token types,
    we handle them explicitly in the lexer.
    `category` is the TokenCategory enum member that describes the category of a token.
    `precedence` is used to determine the order of operations when evaluating logical expressions. Most lexemes don't
    have a precedence, so we use 0 for them. This variable exists mainly to document the precedence defined in RFC 9535,
    and to allow processing of logical expressions using Pratt Parsing if needed (not currently implemented).
    `alternate_repr` is a custom string representation for display of the TokenType in cases where it is desired
    to use an alternate representation, like in TokenType.IDENTIFIER where we use "ID"
    instead of the more verbose "IDENTIFIER"

    """
    
    SPACE    = ( "SPACE", TokenCategory.DELIMITER, )

    """
    Enum terminology, e.g. DOLLAR:
    member       = TokenType.DOLLAR
    member.name  = 'DOLLAR' (the member name)
    member.value = (bnf.DOLLAR, TokenCategory.DELIMITER, )
    """
    
    # single char tokens
    LBRACKET = ( bnf.LEFT_BRACKET           , TokenCategory.DELIMITER          , )
    RBRACKET = ( bnf.RIGHT_BRACKET          , TokenCategory.DELIMITER          , )
    LPAREN   = ( bnf.LEFT_PAREN             , TokenCategory.DELIMITER          , )
    RPAREN   = ( bnf.RIGHT_PAREN            , TokenCategory.DELIMITER          , )
    SQUOTE   = ( bnf.SINGLE_QUOTE           , TokenCategory.DELIMITER          , )
    DQUOTE   = ( bnf.DOUBLE_QUOTE           , TokenCategory.DELIMITER          , )
    COMMA    = ( bnf.COMMA                  , TokenCategory.DELIMITER          , )
    DOT      = ( bnf.DOT                    , TokenCategory.DELIMITER          , )
    DOLLAR   = ( bnf.DOLLAR                 , TokenCategory.DELIMITER          , )
    QMARK    = ( bnf.QUESTION               , TokenCategory.DELIMITER          , )
    STAR     = ( bnf.WILDCARD_SELECTOR      , TokenCategory.DELIMITER          , )
    AT       = ( bnf.AT                     , TokenCategory.DELIMITER          , )
    COLON    = ( bnf.COLON                  , TokenCategory.DELIMITER          , )
    NOT      = ( bnf.LOGICAL_NOT_OP         , TokenCategory.LOGICAL_OPERATOR   , 4 )
    GT       = ( bnf.GREATER_THAN           , TokenCategory.COMPARISON_OPERATOR, 3 )
    LT       = ( bnf.LESS_THAN              , TokenCategory.COMPARISON_OPERATOR, 3 )
    
    
    #multi char tokens
    DOUBLE_DOT = ( bnf.DOUBLE_DOT           , TokenCategory.DELIMITER          , 0 )
    EQUAL      = ( bnf.EQUAL                , TokenCategory.COMPARISON_OPERATOR, 3 )
    NOT_EQUAL  = ( bnf.NOT_EQUAL            , TokenCategory.COMPARISON_OPERATOR, 3 )
    GTE        = ( bnf.GREATER_THAN_OR_EQUAL, TokenCategory.COMPARISON_OPERATOR, 3 )
    LTE        = ( bnf.LESS_THAN_OR_EQUAL   , TokenCategory.COMPARISON_OPERATOR, 3 )
    AND        = ( bnf.LOGICAL_AND_OP       , TokenCategory.LOGICAL_OPERATOR   , 2 )
    OR         = ( bnf.LOGICAL_OR_OP        , TokenCategory.LOGICAL_OPERATOR   , 1 )
    
    # literal types
    # The lexer does not use the lexeme value to scan for these types, they are handled specially with regex matching
    INT        = ( "INT"      , TokenCategory.LITERAL   , )
    FLOAT      = ( "FLOAT"    , TokenCategory.LITERAL   , )
    STRING     = ( "STRING"   , TokenCategory.LITERAL   , )
    SLICE      = ( "SLICE"    , TokenCategory.LITERAL   , )
    
    # IDENTIFIER: used for member-name-shorthand and function names.
    #  We also use this type to store JSON keywords.  The parser will decide if they are identifiers or keywords
    #  according to their use in context
    IDENTIFIER = ("IDENTIFIER", TokenCategory.IDENTIFIER, 0, "ID")
    
    #------------------
    # JSON keywords
    #------------------
    # But only treated as keywords in certain contexts such as logical comparisons.
    # They are allowed as member values,
    #   e.g., { "key1" : "true"} , where the member value is the string "true" and not the JSON value true,
    #   which is distinct from  { "key1": true } ( no quotes around true here )
    #
    # and they are allowed as member names, e.g., { "null" : "foo" }
    # Although these examples might be confusing design choices for a dict and should be avoided,
    # they are syntactically allowed by the spec
    TRUE     = ( bnf.TRUE, TokenCategory.KEYWORD,  )
    FALSE    = ( bnf.FALSE, TokenCategory.KEYWORD, )
    # NULL : Note - JSON null is treated the same as any other JSON value, i.e., it is not taken to mean
    # "undefined" or "missing".
    # Python's json.load(s) properly converts JSON null to Python None.
    NULL     = ( bnf.NULL, TokenCategory.KEYWORD, )
    
    # special
    NO_OP   = ("NO_OP",   TokenCategory.NO_OP, )
    UNKNOWN = ("UNKNOWN", TokenCategory.UNKNOWN, )
    EOF     = ("EOF",     TokenCategory.EOF, )

    def __init__(self, lexeme: str, category: TokenCategory, precedence: int = 0, alternate_repr: str = '') -> None:
        self._lexeme: str = lexeme
        self._category: TokenCategory  = category
        self._precedence = precedence
        self._alternate_repr = alternate_repr
    
    def __repr__(self) -> str:
        string = (f"{self.name}(lexeme={self._lexeme}, category={self._category.name}, "
                  f"precedence={self._precedence}, string_repr={self._alternate_repr})")
        return string
    
    def __str__(self) -> str:
        if self._alternate_repr :
            return f"{self._alternate_repr}"
        else:
            return f"{self._lexeme}"
    
    
    @property
    def lexeme(self) -> str:
        return self._lexeme
    
    @property
    def category(self) -> TokenCategory:
        return self._category
    
    @property
    def precedence(self) -> int:
        return self._precedence
    
    @property
    def alternate_repr(self) -> str:
        return self._alternate_repr

    def is_literal(self) -> bool:
        return self._category == TokenCategory.LITERAL
    
    def is_keyword(self) -> bool:
        return self._category == TokenCategory.KEYWORD
    
    def is_comparison_operator(self) -> bool:
        return self._category == TokenCategory.COMPARISON_OPERATOR
    
    def is_logical_operator(self) -> bool:
        return self._category == TokenCategory.LOGICAL_OPERATOR
    
    def is_delimiter(self) -> bool:
        return self._category == TokenCategory.DELIMITER
    
    def is_identifier(self) -> bool:
        return self._category == TokenCategory.IDENTIFIER


####################################################################
# TokenType LISTS AND SETS
####################################################################

STRING_DELIMETER_LEXEME_SET  = { bnf.SINGLE_QUOTE, bnf.DOUBLE_QUOTE }
COMPARABLE_LITERAL_TYPES_SET = { TokenType.INT, TokenType.FLOAT, TokenType.STRING,
                                 TokenType.TRUE, TokenType.FALSE, TokenType.NULL }
NUMBER_TYPES_SET             = { TokenType.INT, TokenType.FLOAT }

# TOKEN_LOOKUP_DICT: allows us to find a TokenType Enum member from its `lexeme` representation
TOKEN_LOOKUP_DICT = { item.lexeme: item for item in TokenType }
# todo remove debugging prints
# print(f"size of TOKEN_LOOKUP_DICT = {len(TOKEN_LOOKUP_DICT)}") # size of TOKEN_LOOKUP_DICT = 33
# print(f"{TOKEN_LOOKUP_DICT=}")
# display_dict_members(TOKEN_LOOKUP_DICT,single_line=False, quote=False)

# TWO_CHAR_TOKEN_TYPES: a list of TokenTypes composed of two characters. They should be processed
#   before SINGLE_CHAR_TOKEN_TYPES, keywords, identifiers, and literals.
TWO_CHAR_TOKEN_TYPES: list[TokenType] = [
    TokenType.DOUBLE_DOT,
    TokenType.EQUAL,
    TokenType.NOT_EQUAL,
    TokenType.GTE,
    TokenType.LTE,
    TokenType.AND,
    TokenType.OR,
]
TWO_CHAR_LEXEMES_SET = { item.lexeme for item in TWO_CHAR_TOKEN_TYPES }
#print(f"{TWO_CHAR_LEXEMES_SET=}")

# SINGLE_CHAR_TOKEN_TYPES: a list of TokenTypes composed of single characters.
#   They should be processed after TWO_CHAR_TOKEN_TYPES, but before keywords, identifiers, and literals.
#   This list and SINGLE_CHAR_LEXEMES_SET do not include TokenType.SQUOTE nor TokenType.DQUOTE.
#   We handle quotes implicitly when trying to match a string literal via a regex patterm.
#   The list and set also do not contain TokenType.COLON, as we handle this lexeme when
#   trying to match a slice selector. This is the only use of a colon in the grammar.
SINGLE_CHAR_TOKEN_TYPES: list[TokenType] = [
    TokenType.DOT,
    TokenType.LBRACKET, TokenType.RBRACKET,
    TokenType.COMMA,
    TokenType.QMARK,
    TokenType.STAR,
    TokenType.AT,
    TokenType.NOT,
    TokenType.GT,
    TokenType.LT,
    TokenType.LPAREN, TokenType.RPAREN,
    TokenType.DOLLAR
]
SINGLE_CHAR_LEXEMES_SET  = { item.lexeme for item in SINGLE_CHAR_TOKEN_TYPES }

# Future keywords would be defined here
JSON_KEYWORD_TOKEN_TYPES = [ TokenType.TRUE, TokenType.FALSE, TokenType.NULL ]
JSON_KEYWORD_LEXEMES_SET = { item.lexeme for item in JSON_KEYWORD_TOKEN_TYPES }

COMPARISON_OPERATORS_SET = {
    TokenType.EQUAL, TokenType.NOT_EQUAL,
    TokenType.GTE, TokenType.LTE,
    TokenType.GT, TokenType.LT
}


STRING_DELIMETER_TOKEN_TYPES = { TokenType.SQUOTE, TokenType.DQUOTE }

SEGMENT_START_TOKEN_TYPES = (
    TokenType.DOT,          # For .member or .*
    TokenType.LBRACKET,     # For [...]
    TokenType.DOUBLE_DOT    # For ..member, ..*, or ..[...]
)

FILTER_QUERY_FIRST_SET = { TokenType.AT, TokenType.DOLLAR }

# (IDENTIFIER, LPAREN) can also start a test_expr,  as a function call, i.e., 'foo(' but we handle this in basic_expr
TEST_EXPR_FIRST_SET = { TokenType.AT, TokenType.DOLLAR }

SINGULAR_QUERY_FIRST_SET = { TokenType.AT, TokenType.DOLLAR }

####################################################################
# TOKEN
####################################################################

class  Token:
    
    NO_TOKEN: 'Token'
    def __init__(self,
                 token_type: TokenType,
                 position: Position,
                 value: str,
                 )-> None:
        
        self._token_type = token_type
        self._position = position
        self._value: str = value
        
        
    def copy(self) -> 'Token':
        """Return a copy of this token instance. Position is copied as well. """
        token = Token(self._token_type, self._position.copy(), self._value)
        return token
    
    def __repr__(self) -> str:
        #if self.value: return f"[{self.token_type}:{self.value}]"
        #return f"{self.token_type.name}"
        return f"Token(token_type={repr(self.token_type)}, value={repr(self._value)}, position={repr(self._position)})"
    
    def __str__(self) -> str:
        return f"{self.token_type.name}: {self._value}"
        
    def __testrepr__(self) -> str:
        """Representation of Token for testing purposes. If you change this, you may break unit tests. """
        if self.token_type == TokenType.SLICE:
            string = f"SLICE[{self.value}]"
        elif self.token_type.is_literal() or self.token_type.is_identifier():
            string = f"{self.token_type}:{self.value}"
        elif self.token_type.is_keyword():
            string =f"{self.token_type.category.name}:{self.value}"
        elif self.token_type._alternate_repr:
            string = f"{self.token_type._alternate_repr}"
        else:
            string = f"{self.token_type.name}"
        return string
    
    @property
    def length(self) -> int:
        return len(self._value)
    
    @property
    def token_type(self) -> TokenType:
        return self._token_type
    
    @property
    def value(self) -> str:
        return self._value
        
    @property
    def position(self) -> Position:
        return self._position

    @position.setter
    def position(self, position: Position) -> None:
        self._position = position
        
        
    def is_identifier(self) -> bool:
        return self.token_type.is_identifier()
    
# NO_TOKEN: acts as a null object for Tokens, to save having to deal with None checking
# This definition has to be here physically after the declaration for the Token class
# since Python doesn't have forward declarations
Token.NO_TOKEN = Token(TokenType.NO_OP, Position('', 0, 0), "")

