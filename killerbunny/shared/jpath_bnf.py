#  File: jpath_bnf.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

import re
import threading
from typing import Pattern

####################################################################
# ABNF OPERATORS    (Concatenation, Alternatives, etc. )
#
# see sction 3, pg 6, RFC  5234
####################################################################

# noinspection RegExpUnnecessaryNonCapturingGroup
def pattern_str(pattern: str | Pattern[str]) -> str:
    """Return the string representation of the pattern."""
    if isinstance(pattern, str):
        return pattern
    elif isinstance(pattern, Pattern):
        return pattern.pattern
    else:
        raise TypeError(f"Expected str or Pattern[str], got {type(pattern)} '{pattern}'")


def concat(seq: list[str | Pattern[str]]) -> str:
    """Return a regex pattern str that matches the concatenation of the patterns in the sequence.
    I.e., foo bar   (foo followed by bar)
    E.g., calling : concat(['foo', 'bar']) returns the pattern r'(?:(?:foo)(?:bar))'
    """
    patterns: list[str] = []
    for index, item in enumerate(seq):
        patterns.append(f"(?:{pattern_str(item)})")
    return f"(?:{''.join( [ pattern for pattern in patterns ])})"


def alternatives(seq: list[str | Pattern[str]]) -> str:
    """Return a regex pattern str that matches any of the patterns in the sequence.
    I.e., foo | bar
    E.g., calling : alternatives(['foo', 'bar']) returns the pattern r'(?:(?:foo)|(?:bar))'
    """
    
    patterns: list[str] = []
    for item in seq:
        patterns.append(f"(?:{pattern_str(item)})")
    return  f"(?:{'|'.join( [ pattern for pattern in patterns ] )})"

# noinspection RegExpUnnecesaryNonCapturingGroup
def plus_rep(pattern: str | Pattern[str]) -> Pattern[str]:
    """Return a regex pattern that matches the '+' variable repetition of the pattern.
    I.e.,  foo+ ; one or more foo.
    E.g., plus_rep('foo') returns the pattern r'(?:foo)+'
    """
    return re.compile(rf'(?:{pattern_str(pattern)})+')


def star_rep(pattern: str | Pattern[str]) -> str:
    """Return a regex pattern that matches the '*' variable repetition of the pattern.
    I.e., foo* ; foo zero or more times.
    E.g., star_rep('foo') returns the pattern r'(?:foo)*'
    """
    return rf"(?:{pattern_str(pattern)})*"


# noinspection RegExpUnnecessaryNonCapturingGroup
def n_rep(n:int, pattern: str | Pattern[str]) -> Pattern[str]:
    """Return a regex pattern that matches `pattern` exactly n times.
    I.e., in ABNF form : 3foo ; foo exactly 3 times
    E.g., n_rep(2, 'foo') returns the pattern r'(?:foo){2}'
    """
    return re.compile(rf"(?:{pattern_str(pattern)}){JPathBNFConstants.LEFT_BRACE}{n}{JPathBNFConstants.RIGHT_BRACE}")


# noinspection RegExpUnnecessaryNonCapturingGroup,PyShadowingBuiltins
def min_max_rep(min:int, max:int, pattern: str | Pattern[str]) -> Pattern[str]:
    """Return a regex pattern that matches `pattern` between `min` and `max` times.
    I.e., in ABNF form : 2*3foo ; at least 2 foo and not more than 3 foo
    E.g., min_max_rep(2, 3, 'foo') returns the pattern r'(?:foo){2,3}'
    """
    return re.compile(rf'(?:{pattern_str(pattern)}){JPathBNFConstants.LEFT_BRACE}{min},{max}{JPathBNFConstants.RIGHT_BRACE}')

# noinspection RegExpUnnecessaryNonCapturingGroup
def optional(pattern: str | Pattern[str]) -> Pattern[str]:
    """Return a regex pattern that matches the optional repetition of the pattern, i.e., zero or one time.
    I.e., [ foo] ; an optional foo
       same as :  *1(foo) ; foo zero or one times
    E.g., optional('foo') returns the pattern r'(?:foo)?'
    """
    return re.compile(rf"(?:{pattern_str(pattern)})?")


class JPathBNFConstants:
    """ Constants and Python regex str patterns for various terminal and non-terminal symbols defined
    in the RFC 9535 grammar.
    Constants are used primarily by the lexer when creating and defining tokens,
     and in the construction of regular expression patterns.
    Note that these regexes are Python regular expression patters for terinal and non-terminal symbols of the RFC 9535
    grammar that can be expressed as regular expression. They are distinct from the I-regexp patterns defined for use
    in the match() and search() functions
    """
    # Basic characters
    
    SLASH     = SOLIDUS         = chr(0x2F)  # forward slash '/'
    BACKSLASH = REVERSE_SOLIDUS = chr(0x5C)  # backslash '\'
    
    SINGLE_QUOTE = chr(0x27)   # single quote ' character
    DOUBLE_QUOTE = chr(0x22)   # double quote " character
    ESC           = BACKSLASH   # '\'
    UNDERSCORE    = '_'
    COMMA         = ','
    
    # Brackets, braces, and other special characters
    
    LEFT_PAREN    = '('
    RIGHT_PAREN   = ')'
    LEFT_BRACKET  = '['
    RIGHT_BRACKET = ']'
    LEFT_BRACE    = '{'
    RIGHT_BRACE   = '}'
    QUESTION      = '?'
    STAR          = '*'
    PLUS          = '+'
    MINUS         = '-'
    PIPE          = '|'
    CARRET        = '^'
    DOLLAR        = '$'
    DOT           = '.'
    AMPERSAND     = '&'
    TILDE         = '~'
    HASH          = '#'
    AT            = '@'
    COLON         = ':'
    
    DOUBLE_DOT    = '..'

    # comparison operators
    EQUAL                 = '=='
    NOT_EQUAL             = '!='
    GREATER_THAN          = '>'
    GREATER_THAN_OR_EQUAL = '>='
    LESS_THAN             = '<'
    LESS_THAN_OR_EQUAL    = '<='
    
    # logical operators
    LOGICAL_NOT_OP = '!'
    LOGICAL_AND_OP = '&&'
    LOGICAL_OR_OP  = '||'
    
    # JSON keywords. But only treated as keywords in certain contexts
    TRUE     = "true"
    FALSE    = "false"
    # NULL : Note - JSON null is treated the same as any other JSON value, i.e., it is not taken to mean
    # "undefined" or "missing".
    NULL     = "null"
    
    # escaped versions of special characters for use in regular expressions as literals
    BACKSLASH_ESC     = re.escape(BACKSLASH)
    LEFT_PAREN_ESC    = re.escape(LEFT_PAREN)
    RIGHT_PAREN_ESC   = re.escape(RIGHT_PAREN)
    LEFT_BRACKET_ESC  = re.escape(LEFT_BRACKET)
    RIGHT_BRACKET_ESC = re.escape(RIGHT_BRACKET)
    LEFT_BRACE_ESC    = re.escape(LEFT_BRACE)
    RIGHT_BRACE_ESC   = re.escape(RIGHT_BRACE)
    QUESTION_ESC      = re.escape(QUESTION)
    STAR_ESC          = re.escape(STAR)
    PLUS_ESC          = re.escape(PLUS)
    MINUS_ESC         = re.escape(MINUS)
    PIPE_ESC          = re.escape(PIPE)
    CARRET_ESC        = re.escape(CARRET)
    DOLLAR_ESC        = re.escape(DOLLAR)
    DOT_ESC           = re.escape(DOT)
    AMPERSAND_ESC     = re.escape(AMPERSAND)
    TILDE_ESC         = re.escape(TILDE)

    ALPHA    = '[a-zA-Z]'  # todo spec uses these ASCII letters, but should we support full unicode?
    ALPHA_LC = '[a-z]'

    DIGITS          = '0123456789'
    DIGIT_CHAR_SET  = '[0-9]'
    DIGITS1         = '123456789'
    DIGIT1_CHAR_SET = '[1-9]' # non-zero digit
    INT             = f'(?:0|-?{DIGIT1_CHAR_SET}{DIGIT_CHAR_SET}*)'  # no leading zeros allowed in integers
    # START:END:STEP used for slice-selector
    START           = INT                      # inclusive, included in selection
    END             = INT                      # exclusive, not included in selection
    STEP            = INT                      # default = 1
    STEP_DEFAULT:int= 1
    SLICE_CHARS     = f"{DIGITS}:-"  # a slice selector contains these characters (and possible whitespace)
    EXPONENT        = f"[eE][-+]?{DIGIT_CHAR_SET}+"   # decimal exponent
    FRACTION        = rf"\.{DIGIT_CHAR_SET}+"  # decimal fraction
    
    NUMBER      = f'(?P<number>(?P<int_part>{INT}|-0)(?P<frac_part>{FRACTION})?(?P<exp_part>{EXPONENT})?)'
    
    HEXDIGITS   = "[0-9a-fA-F]"
    _2HEXDIGITS = f"{HEXDIGITS}{LEFT_BRACE}2{RIGHT_BRACE}"
    _3HEXDIGITS = f"{HEXDIGITS}{LEFT_BRACE}3{RIGHT_BRACE}"

    BLANK_CHAR = f"{chr(0x20)}{chr(0x09)}{chr(0x0A)}{chr(0x0D)}"  # space, h-tab, line feed/newline, carriage return
    SPACES     = f"(?:[{BLANK_CHAR}]*)"      # zero or more blank characters
    
    # JPath Query Operators
    ROOT_IDENTIFIER         = DOLLAR # '$'
    CURRENT_NODE_IDENTIFIER = AT     # '@'
    WILDCARD_SELECTOR       = STAR   # '*'
    INDEX_SELECTOR          = INT    # decimal integer
    
    # For well-formed semantics, array indices must be within the following range:
    INT_MAX =  (2**53) - 1
    INT_MIN = -(2**53) + 1
    
    # These patterns require non-trivial initialization so they are defined in the _init_grammar_patterns() method
    NON_SURROGATE: str
    HIGH_SURROGATE: str
    LOW_SURROGATE: str
    HEX_CHAR: str
    FUNCTION_NAME_FIRST: str
    FUNCTION_NAME_CHAR: str
    FUNCTION_NAME: str
    NON_SURROGATE_CODEPOINTS: str
    UNESCAPED_CHAR: str
    ESCAPABLE_CHAR: str
    SINGLE_QUOTED: str
    DOUBLE_QUOTED: str
    STRING_LITERAL_DOUBLE_QUOTEABLE: str
    STRING_LITERAL_DQ: str
    STRING_LITERAL_SINGLE_QUOTEABLE: str
    STRING_LITERAL_SQ: str
    STRING_LITERAL: str
    LITERAL: str

    SLICE_SELECTOR: str
    NAME_SELECTOR: str
    INDEX_SEGMENT: str
    NAME_FIRST: str
    NAME_CHAR: str
    MEMBER_NAME_SHORTHAND: str
    NAME_SEGMENT: str
    SINGULAR_QUERY_SEGMENTS: str
    ABSOLUTE_SINGULAR_QUERY: str
    RELATIVE_SINGULAR_QUERY: str
    SINGULAR_QUERY: str
    
    _grammar_patterns_initialized_for_class: dict[ type, bool ] = {}  # Key: class, Value: bool
    _init_patterns_lock = threading.Lock()  # Lock for initializing patterns
    
    @classmethod
    def _init_grammar_patterns(cls) -> None:
        
        # Terminals (not strictly terminals but these can be parsed without further recursion)
        
        ####################################################################
        # HEX_CHAR
        ####################################################################
        # RFC 9535 may be incorrect in the non-surrogate grammar. Below is from the RFC page 54
        # cls.NON_SURROGATE  = f"(?:(?:[0-9A-F]{cls._3HEXDIGITS})|(?:D[0-7]{cls._2HEXDIGITS}))"
        # I have changed NON_SURROGATE to the following, which is more consistent with the JSON spec
        # NON_SURROGATE range: 0x0000-0xD7FF, or 0xE000-0xFFFF
        cls.NON_SURROGATE  = f"(?:[0-9a-cA-C]{cls._3HEXDIGITS})|(?:[dD][0-7]{cls._2HEXDIGITS})|(?:[eEfF]{cls._3HEXDIGITS})"
        cls.HIGH_SURROGATE = f"(?:[dD][89aAbB]{cls._2HEXDIGITS})" # D800 - DBFF
        cls.LOW_SURROGATE  = f"(?:[dD][c-fC-F]{cls._2HEXDIGITS})" # DC00 - DFFF
        cls.HEX_CHAR = f"(?:(?:{cls.NON_SURROGATE})|(?:{cls.HIGH_SURROGATE}{cls.BACKSLASH_ESC}u{cls.LOW_SURROGATE}))"
        
      
        ####################################################################
        # FUNCTION_NAME
        ####################################################################
        cls.FUNCTION_NAME_FIRST = cls.ALPHA_LC
        cls.FUNCTION_NAME_CHAR = alternatives([cls.FUNCTION_NAME_FIRST, cls.UNDERSCORE, cls.DIGIT_CHAR_SET])
        cls.FUNCTION_NAME = concat( [ cls.FUNCTION_NAME_FIRST, star_rep(cls.FUNCTION_NAME_CHAR) ] )
        
        ####################################################################
        # STRING LITERAL    RFC 9535 page 54
        ####################################################################
        cls.NON_SURROGATE_CODEPOINTS = r'[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]'
        # UNESCAPED_CHAR - omits " ' \ and surrogate code points
        #   we need the literal backslash-x-hex digits to make it to the regex as character classes,
        #   so we must escape them by using a raw string here
        cls.UNESCAPED_CHAR = rf'(?:(?:[\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F])|(?:{cls.NON_SURROGATE_CODEPOINTS}))'
        cls.ESCAPABLE_CHAR  = rf'(?:(?:[bfnrt{cls.SLASH}{cls.BACKSLASH_ESC}])|(?:u{cls.HEX_CHAR}))'
        cls.SINGLE_QUOTED = rf"(?:{cls.UNESCAPED_CHAR}|{cls.DOUBLE_QUOTE}|(?:{cls.BACKSLASH_ESC}{cls.SINGLE_QUOTE})|(?:{cls.BACKSLASH_ESC}{cls.ESCAPABLE_CHAR}))"
        cls.DOUBLE_QUOTED = rf"(?:{cls.UNESCAPED_CHAR}|{cls.SINGLE_QUOTE}|(?:{cls.BACKSLASH_ESC}{cls.DOUBLE_QUOTE})|(?:{cls.BACKSLASH_ESC}{cls.ESCAPABLE_CHAR}))"
        cls.STRING_LITERAL_DOUBLE_QUOTEABLE = f"(?P<string_dq>{cls.DOUBLE_QUOTED}*)"
        cls.STRING_LITERAL_SINGLE_QUOTEABLE = f"(?P<string_sq>{cls.SINGLE_QUOTED}*)"
        cls.STRING_LITERAL_DQ = f"(?:{cls.DOUBLE_QUOTE}{cls.STRING_LITERAL_DOUBLE_QUOTEABLE}{cls.DOUBLE_QUOTE})"
        cls.STRING_LITERAL_SQ = f"(?:{cls.SINGLE_QUOTE}{cls.STRING_LITERAL_SINGLE_QUOTEABLE}{cls.SINGLE_QUOTE})"
        # string literals can be quoted as "string" or 'string'
        # STRING_LITERAL and LITERAL are defined here as regex patterns, but they are large and unwieldy and complex.
        # So when trying to match one, it's better to use the component parts instead,
        # i.e., STRING_LITERAL_SQ and STRING_LITERAL_DQ
        cls.STRING_LITERAL = alternatives([cls.STRING_LITERAL_SQ, cls.STRING_LITERAL_DQ])
        cls.LITERAL = rf"{cls.NUMBER}|{cls.STRING_LITERAL}|{cls.TRUE}|{cls.FALSE}|{cls.NULL}"
        
        ####################################################################
        # SELECTORS
        ####################################################################
        cls.INDEX_SELECTOR = cls.INT  # decimal integer
        # SLICE_SELECTOR examples:
        # 3 positions, each position can be negative, empty, or positive (including 0). So that's 3^3 = 27 possible combinations to test.
        # However, Python's slice operator normalizes the indexes to all fit within the length of the sliced array,
        # so the test cases are somewhat reduced
        cls.SLICE_SELECTOR =f"(?:(?:(?P<start>{cls.START}){cls.SPACES})?{cls.COLON}{cls.SPACES}(?P<end>{cls.END})?{cls.SPACES}(?:{cls.COLON}(?:{cls.SPACES}(?P<step>{cls.STEP}))?)?)"
        
        # NAME_SELECTOR: 2.3.1.2. Semantics
        # A name-selector string MUST be converted to a member name M by removing the surrounding quotes and replacing
        # each escape sequence with its equivalent Unicode character, as shown in Table 4:
        # if we allow creation of a NAME_SELECTOR by passing in a string name, we would need to follow this rule
        cls.NAME_SELECTOR = cls.STRING_LITERAL
        
        # FILTER_SELECTOR must be handled in the parser, not here.
        
        ####################################################################
        # SEGMENTS (partial)
        ####################################################################
        
        cls.INDEX_SEGMENT = rf"\[{cls.INDEX_SELECTOR}\]"
        
        cls.NAME_FIRST = alternatives([cls.ALPHA, cls.UNDERSCORE, cls.NON_SURROGATE_CODEPOINTS])
        cls.NAME_CHAR = alternatives([cls.NAME_FIRST, cls.DIGIT_CHAR_SET, ])
        cls.MEMBER_NAME_SHORTHAND = concat( [ cls.NAME_FIRST, star_rep(cls.NAME_CHAR) ] )
        cls.NAME_SEGMENT = rf"(?:\[{cls.NAME_SELECTOR}\])|(?:\.{cls.MEMBER_NAME_SHORTHAND})"

        cls.SINGULAR_QUERY_SEGMENTS = rf"(?:{cls.SPACES}(?:{cls.NAME_SEGMENT}|{cls.INDEX_SEGMENT}))*"
        cls.ABSOLUTE_SINGULAR_QUERY = rf"{cls.ROOT_IDENTIFIER}{cls.SINGULAR_QUERY_SEGMENTS}"
        cls.RELATIVE_SINGULAR_QUERY = rf"{cls.CURRENT_NODE_IDENTIFIER}{cls.SINGULAR_QUERY_SEGMENTS}"
        cls.SINGULAR_QUERY = rf"{cls.RELATIVE_SINGULAR_QUERY}|{cls.ABSOLUTE_SINGULAR_QUERY}"


        cls._grammar_patterns_initialized_for_class[cls] = True
    
    # noinspection PyProtectedMember
    @classmethod
    def _ensure_grammar_initialized(cls) -> None:
        if not cls._grammar_patterns_initialized_for_class.get(cls, False):
            with cls._init_patterns_lock:
                if not cls._grammar_patterns_initialized_for_class.get(cls, False):
                    # If a superclass in MRO also has this mechanism and isn't initialized,
                    # initialize it first. This allows subclasses to build upon initialized superclass patterns.
                    for base in reversed(cls.__mro__[1:]):  # Exclude 'object' and 'cls' itself initially
                        if hasattr(base, "_ensure_grammar_initialized") and \
                                isinstance(getattr(base, "_ensure_grammar_initialized"), classmethod) and \
                                not cls._grammar_patterns_initialized_for_class.get(base, False):
                            # Call the superclass's ensure method.
                            # This assumes that _ensure_grammar_initialized on the base
                            # will correctly initialize 'base's patterns.
                            base._ensure_grammar_initialized()
                    
                    cls._init_grammar_patterns()  # Initialize patterns for the current class 'cls'
    
    # _instances: key: class, value: instance of that class
    _instances: dict[ type['JPathBNFConstants'], 'JPathBNFConstants' ] = { }
    _instance_creation_lock = threading.Lock()

    @classmethod
    def instance(cls) -> 'JPathBNFConstants':
        cls._ensure_grammar_initialized()  # Ensure class attributes are set for 'cls'
        
        if cls not in cls._instances:
            with cls._instance_creation_lock:
                if cls not in cls._instances:
                    cls._instances[cls] = cls()  # Calls __init__
        return cls._instances[cls]
        
        
    def __init__(self) -> None:
        # __init__ is now empty as all state is at the class level.
        # The instance() method ensures class-level patterns are initialized.
        pass

# Example of subclassing to modify regexes.
# Note, in most cases subclassing  JPathBNFConstants might be a necessary step in modifying behavior
# of the json path query interpreter, but it's most probably not sufficient. For example, to allow a trailing comma in
# a selector list would require changes to the parser methods that parse a eelector list. I suspect we'd need
# to refactor the parser logic a bit to make it easier to support extending behavior like this. If the need arises we
# can certainly revist this. But for now, it's out of scope for the task of creating an RFC 9535 compliant JSON Path
# interpreter.
class _RelaxedJPathBNF(JPathBNFConstants):
    # Override a simple constant used in INT pattern construction
    # Current grammar supports leading "-" on ints for negative values, but does not support a leading "+"
    # Original JPathBNFConstants.INT uses "-?"
    # Let's say we want to allow "+" as well for integers.
    # We need to identify which base component contributes to the sign.
    # JPathBNFConstants.INT = f'(?:0|-?{JPathBNFConstants.DIGIT1_CHAR_SET}{JPathBNFConstants.DIGIT_CHAR_SET}*)'
    # We can redefine the whole INT pattern:
    INT = f'(?:0|[-+]?{JPathBNFConstants.DIGIT1_CHAR_SET}{JPathBNFConstants.DIGIT_CHAR_SET}*)'
    
    # Another example : allow trailing commas in bracketed selection lists
    # this is currently enforced in the parser's bracketed_selection() method, where it returns a parse error on
    # trailing commas. we would have to subclass the parser and override bracketed_selection() to enable this new
    # feature. Or perhaps we could push more of these grammar definitions into the the  JPathBNFConstants, and have the
    # Lexer optimize the token stream by accepting the trailing comma but removing that token before the parser
    # gets the list of tokens.
    
# initialize instances
# these inits are needed to initialize the constants defined in _init_grammar_patterns(). Once intiialzed, the
# constants can be accesed as normal via JPathBNFConstants.foo expressions.
JPathBNFConstants.instance()
# subclasses of JPathBNFConstants would call instance() here as well
_RelaxedJPathBNF.instance()  # example of possible sublcassing, not used in our JSON Path interpreter





class JPathNormalizedPathBNF:
    # todo unit tests
    # RFC 9535 page 57
    NORMAL_INDEX_SELECTOR = "(?:0|(?:[1-9][0-9]*))"
    NORMAL_HEXDIGIT  = "[0-9a-f]"
    # NORMAL_HEXCHAR: 0000-0007, 000b, 000e-000f, 0010 - 001f
    NORMAL_HEXCHAR = f"(?:00(?:0[0-7]|0b|0[e-f]|1{NORMAL_HEXDIGIT}))"
    NORMAL_ESCAPABLE = rf"((?:[bfnrt'\\])|(?:u{NORMAL_HEXCHAR}))"
    NORMAL_UNESCAPED = r"(?:[\x20-\x26\x28-\x5B\x5D-\xFF\u0100-\uD7FF\uE000-\uFFFF\U00010000-\U0010FFFF])"
    NORMAL_SINGLE_QUOTED = rf"(?:{NORMAL_UNESCAPED}|(?:\\{NORMAL_ESCAPABLE}))"
    NORMAL_NAME_SELECTOR = f"(?:'{NORMAL_SINGLE_QUOTED}*')"
    NORMAL_SELECTOR = f"(?:{NORMAL_NAME_SELECTOR}|{NORMAL_INDEX_SELECTOR})"
    NORMAL_INDEX_SEGMENT = rf"(?:\[{NORMAL_SELECTOR}\])"
    NORMALIZED_PATH = f"^\\$(?:{NORMAL_INDEX_SEGMENT}*)$"
    


 