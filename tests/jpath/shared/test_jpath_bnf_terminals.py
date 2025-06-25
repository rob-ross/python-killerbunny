
import itertools
import re
import string
from typing import Iterator, Sequence

import pytest

from killerbunny.shared.jpath_bnf import JPathBNFConstants as bnf


def test_jpath_bnf_constants() -> None:
    """And you may ask yourself, aren't you just testing that Python assignment is working correctly?
    Well, if you have ever accidentally hit a key while the cursor was in a random location and saved your file without
    noticing it, then you know why these tests are actually useful. :)
    """
    
    # Basic characters
    assert bnf.SLASH           == chr(0x2F)
    assert bnf.SOLIDUS         == chr(0x2F)
    assert bnf.BACKSLASH       == chr(0x5C)
    assert bnf.REVERSE_SOLIDUS == chr(0x5C)
    assert bnf.SINGLE_QUOTE == chr(0x27)
    assert bnf.DOUBLE_QUOTE == chr(0x22)
    assert bnf.ESC             == chr(0x5C)
    assert bnf.UNDERSCORE      == '_'
    assert bnf.COMMA           == ','
    
    # Brackets, braces, and other special characters
    assert bnf.LEFT_PAREN    == '('
    assert bnf.RIGHT_PAREN   == ')'
    assert bnf.LEFT_BRACKET  == '['
    assert bnf.RIGHT_BRACKET == ']'
    assert bnf.LEFT_BRACE    == '{'
    assert bnf.RIGHT_BRACE   == '}'
    assert bnf.QUESTION      == '?'
    assert bnf.STAR          == '*'
    assert bnf.PLUS          == '+'
    assert bnf.MINUS         == '-'
    assert bnf.PIPE          == '|'
    assert bnf.CARRET        == '^'
    assert bnf.DOLLAR        == '$'
    assert bnf.DOT           == '.'
    assert bnf.AMPERSAND     == '&'
    assert bnf.TILDE         == '~'
    assert bnf.HASH          == '#'
    assert bnf.AT            == '@'
    assert bnf.COLON         == ':'
    
    assert bnf.DOUBLE_DOT == '..'
    
    # Comparison operators
    assert bnf.EQUAL                    == '=='
    assert bnf.NOT_EQUAL                == '!='
    assert bnf.GREATER_THAN             == '>'
    assert bnf.GREATER_THAN_OR_EQUAL    == '>='
    assert bnf.LESS_THAN                == '<'
    assert bnf.LESS_THAN_OR_EQUAL       == '<='
    
    # Logical operators
    assert bnf.LOGICAL_NOT_OP == '!'
    assert bnf.LOGICAL_AND_OP == '&&'
    assert bnf.LOGICAL_OR_OP  == '||'
    
    # Boolean and null constants
    assert bnf.TRUE  ==   "true"
    assert bnf.FALSE ==   "false"
    assert bnf.NULL  ==   "null"
    
    # Escaped versions
    assert bnf.LEFT_PAREN_ESC    == r'\('
    assert bnf.RIGHT_PAREN_ESC   == r'\)'
    assert bnf.LEFT_BRACKET_ESC  == r'\['
    assert bnf.RIGHT_BRACKET_ESC == r'\]'
    assert bnf.LEFT_BRACE_ESC    == r'\{'
    assert bnf.RIGHT_BRACE_ESC   == r'\}'
    assert bnf.QUESTION_ESC      == r'\?'
    assert bnf.STAR_ESC          == r'\*'
    assert bnf.PLUS_ESC          == r'\+'
    assert bnf.MINUS_ESC         == r'\-'
    assert bnf.PIPE_ESC          == r'\|'
    assert bnf.CARRET_ESC        == r'\^'
    assert bnf.DOLLAR_ESC        == r'\$'
    assert bnf.BACKSLASH_ESC     == r'\\'
    assert bnf.DOT_ESC           == r'\.'
    assert bnf.AMPERSAND_ESC     == r'\&'
    assert bnf.TILDE_ESC         == r'\~'
    
    assert bnf.ALPHA           == "[a-zA-Z]"
    assert bnf.ALPHA_LC        == "[a-z]"
    assert bnf.DIGITS          == '0123456789'
    assert bnf.DIGIT_CHAR_SET  == "[0-9]"
    assert bnf.DIGITS1         == '123456789'
    assert bnf.DIGIT1_CHAR_SET == "[1-9]"
    assert bnf.INT             == "(?:0|-?[1-9][0-9]*)"
    assert bnf.START           == "(?:0|-?[1-9][0-9]*)"
    assert bnf.END             == "(?:0|-?[1-9][0-9]*)"
    assert bnf.STEP            == "(?:0|-?[1-9][0-9]*)"
    assert bnf.STEP_DEFAULT    == 1
    assert bnf.SLICE_CHARS     == "0123456789:-"
    assert bnf.EXPONENT        == "[eE][-+]?[0-9]+"
    assert bnf.FRACTION        == r"\.[0-9]+"
    assert bnf.HEXDIGITS       == "[0-9a-fA-F]"
    assert bnf._2HEXDIGITS     == "[0-9a-fA-F]{2}"
    assert bnf._3HEXDIGITS     == "[0-9a-fA-F]{3}"
    
    assert bnf.BLANK_CHAR == " \t\n\r"
    assert bnf.SPACES     == "(?:[ \t\n\r]*)"
    
    # JPath Query Operators
    assert bnf.ROOT_IDENTIFIER          == '$'
    assert bnf.CURRENT_NODE_IDENTIFIER  == '@'
    assert bnf.WILDCARD_SELECTOR        == '*'
    assert bnf.INDEX_SELECTOR           == "(?:0|-?[1-9][0-9]*)"
    
    assert bnf.INT_MAX ==  (2**53) - 1
    assert bnf.INT_MIN == -(2**53) + 1
    
    
    assert bnf.NON_SURROGATE_CODEPOINTS == r'[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]'


####################################################################
# ALPHA
####################################################################

# Test data for ALPHA '[a-zA-Z]'
alpha_tests = [
    ('a', True, "Lowercase letter should match"),
    ('Z', True, "Uppercase letter should match"),
    ('0', False, "Digit should not match"),
    ('_', False, "Underscore should not match"),
    ('\u0100', False, "Unicode letter should not match"),
    ('ab', True, "Multiple letters should  match first letter- only tests single character")
]
@pytest.mark.parametrize("test_input, should_match, msg", alpha_tests)
def test_alpha(test_input: str, should_match: bool, msg: str) -> None:
    """Test that ALPHA correctly matches single ASCII letters a-z and A-Z."""
    pattern_re = re.compile(bnf.ALPHA)
    if should_match:
        assert pattern_re.match(test_input) is not None, msg
    else:
        assert pattern_re.match(test_input) is None, msg

# Test data for ALPHA_LC '[a-z]'
alpha_lc_tests = [
    ('a', True, "Lowercase letter should match"),
    ('Z', False, "Uppercase letter should not match"),
    ('0', False, "Digit should not match"),
    ('_', False, "Underscore should not match"),
    ('\u0100', False, "Unicode letter should not match"),
    ('ab', True, "Multiple letters should  match first letter- only tests single character")
]
@pytest.mark.parametrize("test_input, should_match, msg", alpha_lc_tests)
def test_alpha_lc(test_input: str, should_match: bool, msg: str) -> None:
    """Test that ALPHA_LC correctly matches single ASCII letters a-z."""

    pattern_re = re.compile(bnf.ALPHA_LC)
    if should_match:
        assert pattern_re.match(test_input) is not None, msg
    else:
        assert pattern_re.match(test_input) is None, msg


####################################################################
# DIGITS
####################################################################

# Test data for DIGIT_CHAR_SET '[0-9]'
digit_char_set_tests = [
    ('0', True, "Single digit should match"),
    ('9', True, "Single digit should match"),
    ('a', False, "Letter should not match"),
    ('_', False, "Underscore should not match"),
    ('\u0100', False, "Unicode letter should not match"),
    ('42', True, "Multiple digits should match first character - only tests single character")
]
@pytest.mark.parametrize("test_input, should_match, msg", digit_char_set_tests)
def test_digit_char_set(test_input: str, should_match: bool, msg: str) -> None:
    """Test that DIGIT_CHAR_SET correctly matches single digits 0-9."""

    pattern_re = re.compile(bnf.DIGIT_CHAR_SET)
    if should_match:
        assert pattern_re.match(test_input) is not None, msg
    else:
        assert pattern_re.match(test_input) is None, msg

def test_digit_char_set_all() -> None:
    """Exhaustive test of all digits in DIGIT_CHAR_SET."""

    re_pattern = re.compile(bnf.DIGIT_CHAR_SET)
    for target in string.digits:
        assert re_pattern.match(target),     f"{target} should match re.DIGIT"

# Test data for DIGIT1_CHAR_SET '[1-9]'
digit1_char_set_tests = [
    ('0', False, "0 digit should not match"),
    ('1', True, "Single digit should match"),
    ('9', True, "Single digit should match"),
    ('a', False, "Letter should not match"),
    ('_', False, "Underscore should not match"),
    ('\u0100', False, "Unicode letter should not match"),
    ('42', True, "Multiple digits should match first character - only tests single character"),
    ('12', True, "Multiple digits should match first character- only tests single character"),
    ('02', False, "0 digit should not match- only tests single character"),
]
@pytest.mark.parametrize("test_input, should_match, msg", digit1_char_set_tests)
def test_digit1_char_set(test_input: str, should_match: bool, msg: str) -> None:
    """Test that DIGIT1_CHAR_SET correctly matches single digits 1-9."""

    pattern_re = re.compile(bnf.DIGIT1_CHAR_SET)
    if should_match:
        assert pattern_re.match(test_input) is not None, msg
    else:
        assert pattern_re.match(test_input) is None, msg

def test_digit1_all() -> None:
    """Exhaustive test of all digits in DIGIT1_CHAR_SET."""

    re_pattern = re.compile(bnf.DIGIT1_CHAR_SET)
    for index in range(1, len(string.digits)): # skipping 0
        target = string.digits[index]
        assert re_pattern.match(target),      f"{target} DIGIT1.re matches 1-9"
    # 0 should fail
    assert not re_pattern.match('0'),            "DIGIT1.re doesn't match '0'"


####################################################################
# INT
####################################################################

# Test data for INT '(?:0|-?[1-9][0-9]*)'
# also tests START, END, STEP, since they are all equal to INT
int_tests = [
    ('0', True, "Single digit should match"),
    ('9', True, "Single digit should match"),
    ('a', False, "Letter should not match"),
    ('_', False, "Underscore should not match"),
    ('\u0100', False, "Unicode letter should not match"),
    ('42', True, "Multiple digits should match"),
    ('00', False, "Leading 0 digit should not match"),
    ('01', False, "Leading 0 digit should not match"),
    ('1234', True, "Multiple digits should match"),
    ('-1234', True, "Negative number should match"),
    ('- 1', False, "Negative number with space should not match"),

]
@pytest.mark.parametrize("test_input, should_match, msg", int_tests)
def test_int(test_input: str, should_match: bool, msg: str) -> None:
    """Test that INT correctly matches integer strings. """

    pattern_re = re.compile(f"^(?P<value>{bnf.INT})$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("value") == test_input, "Should capture the entire matched string as 'value' group"
    else:
        assert pattern_re.match(test_input) is None, msg

# Test data for EXPONENT "e[-+][0-9]+"
exponent_tests = [
    ('e-0', True, "Single neg digit should match"),
    ('e+0', True, "Single pos digit should match"),
    ('e0', True, "Optional sign not present"),
    ('e-00123', True, "Multiple neg digits should match"),
    ('e+00123', True, "Multiple pos digits should match"),
    ('e00123', True, "Multiple pos digits with no sign should match"),
    ('E-123', True, "Uppercase E should match"),
    ('E+123', True, "Lowercase e should match"),
    ('0', False, "Single 0 should not match"),
    ('+9', False, "Pos digit with no 'e' should  not match"),
    ('-9', False, "Neg digit with no 'e' should  not match"),
    ('a', False, "non-e Letter should not match"),
    ('-', False, "Minus should not match"),
    ('+', False, "Plus should not match"),
    ('E+', False, "pos Prefix with no digits should not match"),
    ('E-', False, "neg Prefix with no digits should not match"),
    ('E+a', False, "pos Prefix with no digits should not match"),
    ('E-a', False, "neg Prefix with no digits should not match"),
    ('\u0100', False, "Unicode letter should not match"),
    ('42', False, "Multiple digits should not match"),
    ('0e-123', False, "Leading 0 digit should not match"),
    ('01E+123', False, "Leading 0 digit should not match"),
    ('1234', False, "Integer digits should not match"),
    ('-1234', False, "Negative number should not match"),
]
@pytest.mark.parametrize("test_input, should_match, msg", exponent_tests)
def test_exponent(test_input: str, should_match: bool, msg: str) -> None:
    """Test that INT correctly matches integer strings. """

    pattern_re = re.compile(f"^(?P<value>{bnf.EXPONENT})$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("value") == test_input, "Should capture the entire matched string as 'value' group"
    else:
        assert pattern_re.match(test_input) is None, msg

fraction_tests = [
    ('.0', True, "Single digit should match"),
    ('.9', True, "Single digit should match"),
    ('.1234', True, "Multiple digits should match"),
    ('a', False, "Letter should not match"),
    ('_', False, "Underscore should not match"),
    ('\u0100', False, "Unicode letter should not match"),
    ('42', False, "Multiple digits no dot should not match"),
    ('0.0', False, "Leading 0 digit doesn't match"),
    ('01', False, "Leading 0 digit should not match"),
]
# Test data for FRACTION rf"\.[0-9]]+"
@pytest.mark.parametrize("test_input, should_match, msg", fraction_tests)
def test_fraction(test_input: str, should_match: bool, msg: str) -> None:
    """Test that INT correctly matches integer strings. """

    pattern_re = re.compile(f"^(?P<value>{bnf.FRACTION})$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("value") == test_input, "Should capture the entire matched string as 'value' group"
    else:
        assert pattern_re.match(test_input) is None, msg


# Test data for NUMBER
# '(?P<number>(?P<int_part>(?:0|-?[1-9][0-9]*)|-0)(?P<frac_part>\.[0-9]+)?(?P<exp_part>[eE][-+][0-9]+)?)'
number_tests = [
    ('0', True, "Single 0 should match"),
    ('-0', True, "Negative 0 should match"),
    ("10", True, "10 should match"),
    ("-10", True, "-10 should match"),
    ("01", False, "Leading 0 digit should not match"),
    ("0.0", True, "Single leading zero should match"),
    ("00.0", False, "Double leading zero should not match"),
    
    ("0e-123", True, "Leading 0 digit should match"),
    ("01E+123", False, "Leading 0 digit should not match"),
    ("1234", True, "Integer digits should match"),
    ("-1234", True, "Negative number should match"),
    ("1.0", True, "Single digit should match"),
    ("1.9", True, "Single digit should match"),
    ("1.1234", True, "Multiple digits should match"),
    ("1.0000", True, "Multiple digits should match"),
    ("123.0e-32", True, "All three parts match"),
    ("-123.031e+32", True, "All three parts match"),
    ("e+10", False, "Exponent with no leading digits doesn't match"),
    (".124", False, "Fraction requires leading digit"),
    ("0.124", True, "Fraction includes leading zero"),
]
@pytest.mark.parametrize("test_input, should_match, msg", number_tests)
def test_number(test_input: str, should_match: bool, msg: str) -> None:

    re_pattern = re.compile(f"^{bnf.NUMBER}$")
    match = re_pattern.match(test_input)
    if should_match:
        assert match is not None, msg
        assert test_input == match.group("number"), "Should capture the entire matched string as 'number' group"
    else:
        assert match is None, msg


####################################################################
# HEXDIGITS
####################################################################


def test_hexdigits() -> None:
    """Exhaustive test of all hex digits from 0-F, upper and lower case"""

    re_pattern = re.compile(bnf.HEXDIGITS)
    for i in range(0x00, 0x0F + 1):
        target_upper = f'{i:01X}'
        target_lower = f'{i:01x}'
        assert re_pattern.match(target_upper),     f"{target_upper} should match re.HEXDIG"
        assert re_pattern.match(target_lower),     f"{target_lower} should match re.HEXDIG"


def test_2hexdigits() -> None:
    """Exhaustive test of all hex digits from 00-FF, upper and lower case"""


    re_pattern = re.compile(bnf._2HEXDIGITS)
    for i in range(0x00, 0xFF + 1):
        target_upper = f'{i:02X}'
        target_lower = f'{i:02x}'
        assert re_pattern.match(target_upper), f"{target_upper} should match re._2HEXDIG"
        assert re_pattern.match(target_lower), f"{target_lower} should match re._2HEXDIG"


def test_3hexdigits() -> None:
    """Exhaustive test of all hex digits from 000-FFF, upper and lower case"""

    re_pattern = re.compile(bnf._3HEXDIGITS)
    for i in range(0x00, 0xFFF + 1):
        target_upper = f'{i:03X}'
        target_lower = f'{i:03x}'
        assert re_pattern.match(target_upper), f"{target_upper} should match re._3HEXDIG"
        assert re_pattern.match(target_lower), f"{target_lower} should match re._3HEXDIG"


####################################################################
# HEX_CHAR / SURROGATES
####################################################################

def test_high_surrogate() -> None:
    # self.HIGH_SURROGATE = f"(?:D[8-B]{self._2HEXDIGITS})"
    # HIGH_SURROGATE should match 0xD800 - 0xDBFF

    re_pattern = re.compile(bnf.HIGH_SURROGATE)
    for i in range(0xD800, 0xDBFF+1):
        target =  f'{i:04X}'
        assert re_pattern.match(target), f"{target=} matches HIGH_SURROGATE.re"

    for target in ["D7FF","DC00"]: # outside range, should not match
        assert not re_pattern.match(target), f"HIGH_SURROGATE.re doesn't match '{target}'"

def test_low_surrogate() -> None:
    # self.LOW_SURROGATE  = f"(?:D[C-F]{self._2HEXDIGITS})"
    # LOW_SURROGATE should match 0xDC00 - 0xDFFF

    re_pattern = re.compile(bnf.LOW_SURROGATE)
    for i in range(0xDC00, 0xDFFF+1):
        target =  f'{i:04X}'
        assert re_pattern.match(target), f"{target=} matches LOW_SURROGATE.re"
    
    for target in ["DBFF","E000"]: # outside range, should not match
        assert not re_pattern.match(target), f"LOW_SURROGATE.re doesn't match '{target}'"

def test_non_surrogate() -> None:
    # self.NON_SURROGATE  = '(?:[0-9A-C][0-9A-F]{3})|(?:D[0-7][0-9A-F]{2})|(?:[E-F][0-9A-F]{3})'
    # should match 0x0000-0xD7FF or 0xE000-0xFFFF

    re_pattern = re.compile(bnf.NON_SURROGATE)
    for i in range(0x0000, 0xD7FF+1):  # should all match
        target =  f'{i:04X}'
        assert re_pattern.match(target), f"{target=} matches NON_SURROGATE.re"
    for i in range(0xD8000, 0xDFFF+1):  # non should match
        target =  f'{i:04X}'
        assert not re_pattern.match(target), f"{target=} doesn't match matches NON_SURROGATE.re"
    for i in range(0xE000, 0xFFFF+1):  # should all match
        target =  f'{i:04X}'
        assert re_pattern.match(target), f"{target=} matches NON_SURROGATE.re"


# noinspection SpellCheckingInspection
def test_hex_char() -> None:
    #self.HEX_CHAR = '(?:(?:[0-9A-C][0-9A-F]{3})|(?:D[0-7][0-9A-F]{2})|(?:[E-F][0-9A-F]{3}))|(?:(?:D[8-B][0-9A-F]{2})\\u(?:D[C-F][0-9A-F]{2}))'
    # should match:
    # 0x0000-0xD7FF
    # 0xE000-0xFFFF
    

    re_pattern = re.compile(bnf.HEX_CHAR)
    # first test the single code points:
    for i in range(0x0000, 0xD7FF+1):  # should all match
        target =  f'{i:04X}'
        assert re_pattern.match(target),     f"{target=} matches HEX_CHAR.re"
    for i in range(0xD800, 0xDFFF+1):  # none should match
        # also tests High surrogate without \\u and low surrogate
        target =  f'{i:04X}'
        assert not re_pattern.match(target),     f"{target=} doesn't match matches HEX_CHAR.re"
    for i in range(0xE000, 0xFFFF+1):  # should all match
        target =  f'{i:04X}'
        assert re_pattern.match(target),     f"{target=} matches HEX_CHAR.re"
        
    # step values used below to allow full range testing without having to exhaustively test every value in the larger
    # ranges
    
    # now test the surrogate pairs
    # D800\uDC00 through DBFF\uDFFF are successfully matched
    for high_rage in range(0xD800, 0xDBFF + 1, 4):
        high_target = f'{high_rage:04X}'
        for low_rage in range(0xDC00, 0xDFFF + 1, 4):
            low_target = f'{low_rage:04X}'
            target = high_target + '\\u' + low_target
            assert re_pattern.match(target),     f"{target=} matches HEX_CHAR.re"
    
    # BAD SURROGATE PAIRS
    # --------------------
    # High surrogate followed by wrong separator
    for high_rage in range(0xD800, 0xDBFF + 1):
        high_target = f'{high_rage:04X}'
        target = high_target + 'u' + '1234'
        assert not re_pattern.match(target),     f"{target=} doesn't match matches HEX_CHAR.re"
        
   # Low surrogate without preceding high surrogate
    for low_rage in range(0xDC00, 0xDFFF + 1):
        low_target = f'{low_rage:04X}'
        target = '\\u' + low_target
        assert not re_pattern.match(target),     f"{target=} doesn't match matches HEX_CHAR.re"

    # High surrogate with invalid low surrogate
    for high_rage in range(0xD800, 0xDBFF + 1, 2):
        high_target = f'{high_rage:04X}'
        for low_rage in range(0x0000, 0x00FF + 1):
            low_target = f'{low_rage:04X}'
            target = high_target + '\\u' + low_target
            assert not re_pattern.match(target),     f"{target=} doesn't match HEX_CHAR.re"
    for high_rage in range(0xD800, 0xDBFF + 1, 2):
        high_target = f'{high_rage:04X}'
        for low_rage in range(0xE000, 0xE0FF + 1):
            low_target = f'{low_rage:04X}'
            target = high_target + '\\u' + low_target
            assert not re_pattern.match(target),     f"{target=} doesn't match HEX_CHAR.re"
            
            
    # Low surrogate with invalid high surrogate
    # todo this currently passes because the first alternative matches any "invalid" surrogate range.
    # we can make the re pattern greedy and force it to match the entire string, but I'll wait to see how
    # using re for the lexer/tokenizer needs to work first.
    for high_rage in range(0x00FF, 0x0FFF + 1, 2):
        high_target = f'{high_rage:04X}'
        for low_rage in range(0xDC00, 0xDFFF + 1, 2):
            low_target = f'{low_rage:04X}'
            target = high_target + '\\u' + low_target
            assert re_pattern.match(target),     f"{target=} matches HEX_CHAR.re"
        
        
####################################################################
# FUNCTION_NAME
####################################################################

function_name_tests = [
    ("0bad_name", False,"Function names cannot start with a number" ),
    ("_good_name", False, "Function names cannot start with an underscore"),
    ("!bad_name", False,"Function names cannot start with a symbol" ),
    ("Bad_name", False, "Function names cannot start with an uppercase letter" ),
    ("bad_namE", False, "Function names cannot contain uppercase letters"),
    ("bad-name", False, "Function names cannot contain symbols"),
    ("good_name", True, "Function names are lowercase and can contain underscore"),
    ("ok_name007", True, "Function names are lowercase and can contain digits"),
    ("a_1_2_3_4_5", True, "Function names start with a lowercase letter.")
]
@pytest.mark.parametrize("test_input, should_match, msg", function_name_tests)
def test_function_name(test_input: str, should_match: bool, msg: str) -> None:
    """Test that FUNCTION_NAME properly matches valid function names and rejects invalid function names."""

    pattern_re = re.compile(f"^(?P<value>{bnf.FUNCTION_NAME})$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("value") == test_input, "Should capture the entire matched string as 'value' group"
    else:
        assert pattern_re.match(test_input) is None, msg
    
    r"""
    Non-Surrogate codepoint Ranges:
    -------------------------------
    \x00   - \x7F   : no match
    \x80   - \xFF   : match
    \u0100 - \uD7FF : match
    \uD800 - \uDFFF : no match
    \uE000 - \uFFFF : match
    \U00010000 - \U0010FFFF : match
    \U00110000 - \UFFFFFFFF : no match
    """
non_surrogate_codepoints_tests = [
    ("\x00", False, "Below 80 should not match" ),
    ("\x47", False, "Below 80 should not match" ),
    ("\x7F", False, "Below 80 should not match" ),
    
    ("\x80", True, "Range 80-FF should match" ),
    ("\xA7", True, "Range 80-FF should match" ),
    ("\xFF", True, "Range 80-FF should match" ),
    
    ("\u0100", True, "Range 0100-D7FF should match" ),
    ("\u4777", True, "Range 0100-D7FF should match" ),
    ("\uD7FF", True, "Range 0100-D7FF should match" ),
    
    ("\uD800", False, "Range D800-DFFF should not match" ),
    ("\uDBFF", False, "Range D800-DFFF should not match" ),
    ("\uDFFF", False, "Range D800-DFFF should not match" ),
    
    ("\uE000", True, "Range E000-FFFF should match" ),
    ("\uE7FF", True, "Range E000-FFFF should match" ),
    ("\uFFFF", True, "Range E000-FFFF should match" ),
    
    ("\U00010000", True, "Range 00010000-0010FFFF should match" ),
    ("\U000FFFFF", True, "Range 00010000-0010FFFF should match" ),
    ("\U0010FFFF", True, "Range 00010000-0010FFFF should match" ),
    
    # Outside of unicode rage, Python can't even decode them
    # ("\U00110000", False, "Range 00110000-FFFFFFFF should match" ),
    # ("\U7FFFFFFF", False, "Range 00110000-FFFFFFFF should match" ),
    # ("\UFFFFFFFF", False, "Range 00110000-FFFFFFFF should match" ),
]
@pytest.mark.parametrize("test_input, should_match, msg", non_surrogate_codepoints_tests)
def test_non_surrogate_codepoints(test_input: str, should_match: bool, msg: str) -> None:
    """ Test parsing of non-surrogate codepoints
    r'[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]'
    """

    pattern_re = re.compile(f"^(?P<value>{bnf.NON_SURROGATE_CODEPOINTS})$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("value") == test_input, "Should capture the entire matched string as 'value' group"
    else:
        assert pattern_re.match(test_input) is None, msg
        
        
unescaped_char_tests = [
    # exclude all control characters
    ("\x00", False, "Below 20 should not match" ),
    ("\x10", False, "Below 20 should not match" ),
    ("\x1F", False, "Below 20 should not match" ),
    
    ("\x20", True, "Space character should match" ),
    ("\x21", True, "Bang ! character should match" ),
    ("\x22", False, "Double quote should not match" ), # exclude double quote "
    
    ("\x23", True, "Pound # sign should match" ),
    ("\x26", True, "Ampersand & should match" ),
    ("\x27", False, "Single quote ' should not match" ),  # exclude single quote '
    
    ("\x28", True, "Left paren ( should match" ),
    ("\x3F", True, "Question mark ? should match" ),
    ("\x5B", True, "Left bracket [ should match" ),
    
    ("\x5C", False, r"Backslash \ should not match" ),  # exclude backslash \
    
    ("\x5D", True, "Right bracket ] should match" ),
    ("\x6F", True, "Right bracket ] should match" ),
    ("\x7F", True, "o character should match" ),
]
joined_tests = unescaped_char_tests + non_surrogate_codepoints_tests[3:]  # skip first three since they would fail here
@pytest.mark.parametrize("test_input, should_match, msg", joined_tests)
def test_unescaped_char(test_input: str, should_match: bool, msg: str) -> None:
    """Test matching of UNESCAPED_CHAR. Matches the same as NON_SURROGATE_CODEPOINTS plus most of range \x20 - 7F.
    It does not match control characters nor " ' \ nor surrogate code points.
    Range is [\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F] + NON_SURROGATE_CODEPOINTS ranges
    (?:(?:[\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F])|(?:[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]))
    """

    pattern_re = re.compile(f"^(?P<value>{bnf.UNESCAPED_CHAR})$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("value") == test_input, "Should capture the entire matched string as 'value' group"
    else:
        assert pattern_re.match(test_input) is None, msg



def test_escapable_char() -> None:
    """Test matching of ESCAPABLE_CHAR. ESCAPABLE_CHAR matches HEX_CHAR along with a few letters:[ bfnrt ]
    HEX_CHAR is tested thoroughly above.
    
    ESCAPABLE_CHAR =
    '(?:(?:[bfnrt/\\])|(?:u(?:(?:(?:[0-9a-cA-C][0-9a-fA-F]{3})|(?:[dD][0-7][0-9a-fA-F]{2})|(?:[eEfF][0-9a-fA-F]{3}))|(?:(?:[dD][89aAbB][0-9a-fA-F]{2})\\u(?:[dD][c-fC-F][0-9a-fA-F]{2})))))'
    
    (?:[bfnrt/\\\\])|  # the 4 backslashes here will match a signgle backslash character in the target string
    (?:u(?:(?:[0-9A-C][0-9A-F]{3})|(?:D[0-7][0-9A-F]{2})|   # this line and the next match HEX_CHAR
    (?:[E-F][0-9A-F]{3}))|(?:(?:D[8-B][0-9A-F]{2})\\\\u(?:D[C-F][0-9A-F]{2})))
    
    """

    pattern_re = re.compile(bnf.ESCAPABLE_CHAR)
    # The pattern should contain actual slash and backslash characters
    assert '/' in bnf.ESCAPABLE_CHAR
    assert '\\' in bnf.ESCAPABLE_CHAR
    # Simple escapes
    for char in 'bfnrt/\\':
        assert pattern_re.match(char), f"'{char}' should match ESCAPABLE_CHAR"
    
    # Invalid escapes
    for char in 'acdeghijklmopqsvwxyz':
        assert not pattern_re.match(char), f"'{char}' should not match ESCAPABLE_CHAR"
    
    # Test that 'u' prefix works with a few sample HEX_CHAR values
    assert pattern_re.match('u0041')  # 'A'
    assert pattern_re.match('uE000')  # First private use area
    assert pattern_re.match('uD800\\uDC00')  # First surrogate pair
    assert pattern_re.match('uDBFF\\uDFFF')  # Last surrogate pair

single_quoted_tests = [
    ('"', True, "Double quote should match"),
    (r'\'', True, "Escaped single quote should match"),
    (r'\"', False, "Escaped double quote should not match"),
    ("'", False, "unescaped single quote should not match"),
    # UNESCAPED_CHAR alternative
    ("\x00", False, "Below 20 should not match" ),
    ("\x10", False, "Below 20 should not match" ),
    ("\x1F", False, "Below 20 should not match" ),
    
    ("\x20", True, "Space character should match" ),
    ("\x21", True, "Bang ! character should match" ),
    
    ("\x23", True, "Pound # sign should match" ),
    ("\x26", True, "Ampersand & should match" ),
    ("\x27", False, "Single quote ' should not match" ),  # exclude single quote '
    
    ("\x28", True, "Left paren ( should match" ),
    ("\x3F", True, "Question mark ? should match" ),
    ("\x5B", True, "Left bracket [ should match" ),
    
    ("\x5C", False, r"Backslash \ should not match" ),  # exclude backslash \
    
    ("\x5D", True, "Right bracket ] should match" ),
    ("\x6F", True, "Right bracket ] should match" ),
    ("\x7F", True, "o character should match" ),
    #Backslashes followed by an ESCAPEABLE_CHAR match
    # 'bfnrt/\\'
    (r'\b', True, "backslash b should match"),
    (r'\f', True, "backslash f should match"),
    (r'\n', True, "backslash n should match"),
    (r'\r', True, "backslash r should match"),
    (r'\t', True, "backslash t should match"),
    (r'\/', True, "backslash / should match"),
    ('\x5C\x5C', True, r"backslash-backslash should match"),
    ('\x5C', False, r"backslash should not match"),
    # These same chars should match without a backlash as UNESCAPED_CHAR alternative
    (r'b', True, "b should match"),
    (r'f', True, "f should match"),
    (r'n', True, "n should match"),
    (r'r', True, "r should match"),
    (r't', True, "t should match"),
    (r'/', True, "/ should match"),
    # A few HEX_CHAR alternatives
    # unescaped should fail:
    (r'u0041', False, "Unescaped A should not match"),
    (r'uE000', False, "Unescaped \uE000 should not match"),
    (r'uD800\uDC00', False, "Unescaped first surrogate pair should not match"),
    (r'uDBFF\uDFFF', False, "Unescaped last surrogate pair should not match"),
    # escaped should match:
    (r'\u0041', True, "A should match"),
    (r'\uE000', True, "\uE000 should match"),
    (r'\uD800\uDC00', True, "First surrogate pair should match"),
    (r'\uDBFF\uDFFF', True, "Last surrogate pair should match"),
]

@pytest.mark.parametrize("test_input, should_match, msg", single_quoted_tests )
def test_single_quoted(test_input: str, should_match: bool, msg: str) -> None:
    """Test matching of SINGLE_QUOTED. This regex is composed of four alternates.
    Two have been tested above: UNESCAPED_CHAR and ESCAPABLE_CHAR
    This test focuses on the other two alternatives
    SINGLE_QUOTED =
    (?:(?:(?:[\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F])|(?:[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]))|"|(?:\\')|(?:\\(?:(?:[bfnrt/\\])|(?:u(?:(?:(?:[0-9a-cA-C][0-9a-fA-F]{3})|(?:[dD][0-7][0-9a-fA-F]{2})|(?:[eEfF][0-9a-fA-F]{3}))|(?:(?:[dD][89aAbB][0-9a-fA-F]{2})\\u(?:[dD][c-fC-F][0-9a-fA-F]{2})))))))
    """

    pattern_re = re.compile(f"^(?P<value>{bnf.SINGLE_QUOTED})$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("value") == test_input, "Should capture the entire matched string as 'value' group"
    else:
        assert pattern_re.match(test_input) is None, msg
        
double_quoted_tests = [
    ('"', False, "Double quote should not match"),
    (r'\'', False, "Escaped single quote should not match"),
    (r'\"', True, "Escaped double quote should match"),
    ("'", True, "Single quote should match"),
    # UNESCAPED_CHAR alternative
    ("\x00", False, "Below 20 should not match" ),
    ("\x10", False, "Below 20 should not match" ),
    ("\x1F", False, "Below 20 should not match" ),
    
    ("\x20", True, "Space character should match" ),
    ("\x21", True, "Bang ! character should match" ),
    
    ("\x23", True, "Pound # sign should match" ),
    ("\x26", True, "Ampersand & should match" ),
    
    ("\x28", True, "Left paren ( should match" ),
    ("\x3F", True, "Question mark ? should match" ),
    ("\x5B", True, "Left bracket [ should match" ),
    
    ("\x5C", False, r"Backslash \ should not match" ),  # exclude backslash \
    
    ("\x5D", True, "Right bracket ] should match" ),
    ("\x6F", True, "Right bracket ] should match" ),
    ("\x7F", True, "o character should match" ),
    #Backslashes followed by an ESCAPEABLE_CHAR match
    # 'bfnrt/\\'
    (r'\b', True, "backslash b should match"),
    (r'\f', True, "backslash f should match"),
    (r'\n', True, "backslash n should match"),
    (r'\r', True, "backslash r should match"),
    (r'\t', True, "backslash t should match"),
    (r'\/', True, "backslash / should match"),
    ('\x5C\x5C', True, r"backslash-backslash should match"),
    ('\x5C', False, r"backslash should not match"),
    # These same chars should match without a backlash as UNESCAPED_CHAR alternative
    (r'b', True, "b should match"),
    (r'f', True, "f should match"),
    (r'n', True, "n should match"),
    (r'r', True, "r should match"),
    (r't', True, "t should match"),
    (r'/', True, "/ should match"),
    # A few HEX_CHAR alternatives
    # unescaped should fail:
    (r'u0041', False, "Unescaped A should not match"),
    (r'uE000', False, "Unescaped \uE000 should not match"),
    (r'uD800\uDC00', False, "Unescaped first surrogate pair should not match"),
    (r'uDBFF\uDFFF', False, "Unescaped last surrogate pair should not match"),
    # escaped should match:
    (r'\u0041', True, "A should match"),
    (r'\uE000', True, "\uE000 should match"),
    (r'\uD800\uDC00', True, "First surrogate pair should match"),
    (r'\uDBFF\uDFFF', True, "Last surrogate pair should match"),
]
@pytest.mark.parametrize("test_input, should_match, msg", double_quoted_tests )
def test_double_quoted(test_input: str, should_match: bool, msg: str) -> None:
    """Test matching of DOUBLE_QUOTED. This regex is composed of four alternates.
    Two have been tested above: UNESCAPED_CHAR and ESCAPABLE_CHAR
    This test focuses on the other two alternatives
    DOUBLE_QUOTED =
    (?:(?:(?:[\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F])|(?:[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]))|'|(?:\\")|(?:\\(?:(?:[bfnrt/\\])|(?:u(?:(?:(?:[0-9a-cA-C][0-9a-fA-F]{3})|(?:[dD][0-7][0-9a-fA-F]{2})|(?:[eEfF][0-9a-fA-F]{3}))|(?:(?:[dD][89aAbB][0-9a-fA-F]{2})\\u(?:[dD][c-fC-F][0-9a-fA-F]{2})))))))
    """

    pattern_re = re.compile(f"^(?P<value>{bnf.DOUBLE_QUOTED})$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("value") == test_input, "Should capture the entire matched string as 'value' group"
    else:
        assert pattern_re.match(test_input) is None, msg


string_literal_double_quotable_tests = [
    ('"', False, "Double quote should not match"),
    (r'\'', False, "Escaped single quote should not match"),
    (r'\"', True, "Escaped double quote should match"),
    ("'", True, "Single quote should match"),
    ("", True, "Empty string should match"),
    ("'foo'", True, "String with single quotes should match"),
    ('"foo"', False, "String with double quotes should not match"),
]
@pytest.mark.parametrize("test_input, should_match, msg", string_literal_double_quotable_tests )
def test_string_literal_double_quotable(test_input: str, should_match: bool, msg: str) -> None:
    """
    Test matching of STRING_LITERAL_DOUBLE_QUOTEABLE. This matches zero or more DOUBLE_QUOTED, which is tested above.
    
    STRING_LITERAL_DOUBLE_QUOTEABLE =
    (?P<string_dq>(?:(?:(?:[\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F])|(?:[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]))|'|(?:\\")|(?:\\(?:(?:[bfnrt/\\])|(?:u(?:(?:(?:[0-9a-cA-C][0-9a-fA-F]{3})|(?:[dD][0-7][0-9a-fA-F]{2})|(?:[eEfF][0-9a-fA-F]{3}))|(?:(?:[dD][89aAbB][0-9a-fA-F]{2})\\u(?:[dD][c-fC-F][0-9a-fA-F]{2})))))))*)

    """

    pattern_re = re.compile(f"^{bnf.STRING_LITERAL_DOUBLE_QUOTEABLE}$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("string_dq") == test_input, "Should capture the entire matched string as 'string_dq' group"
    else:
        assert pattern_re.match(test_input) is None, msg


string_literal_single_quotable_tests = [
    ('"', True, "Double quote should match"),
    (r'\'', True, "Escaped single quote should match"),
    (r'\"', False, "Escaped double quote should not match"),
    ("'", False, "Single quote should not match"),
    ("", True, "Empty string should match"),
    ("'foo'", False, "String with single quotes should not match"),
    ('"foo"', True, "String with double quotes should match"),

]
@pytest.mark.parametrize("test_input, should_match, msg", string_literal_single_quotable_tests )
def test_string_literal_single_quotable(test_input: str, should_match: bool, msg: str) -> None:
    """
    Test matching of STRING_LITERAL_SINGLE_QUOTEABLE. This matches zero or more SINGLE_QUOTED, which is tested above.

    STRING_LITERAL_SINGLE_QUOTEABLE =
    (?P<string_sq>(?:(?:(?:[\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F])|(?:[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]))|"|(?:\\')|(?:\\(?:(?:[bfnrt/\\])|(?:u(?:(?:(?:[0-9a-cA-C][0-9a-fA-F]{3})|(?:[dD][0-7][0-9a-fA-F]{2})|(?:[eEfF][0-9a-fA-F]{3}))|(?:(?:[dD][89aAbB][0-9a-fA-F]{2})\\u(?:[dD][c-fC-F][0-9a-fA-F]{2})))))))*)

    """

    pattern_re = re.compile(f"^{bnf.STRING_LITERAL_SINGLE_QUOTEABLE}$")
    if should_match:
        assert (m:= pattern_re.match(test_input)) is not None, msg
        assert m.group("string_sq") == test_input, "Should capture the entire matched string as 'string_sq' group"
    else:
        assert pattern_re.match(test_input) is None, msg



string_literal_dq_tests = [
    ('""', True, "Empty string should match"),
    ("''", False, "Single quoted empty string should not match"),
    
    ('"a"', True, "String with one character should match"),
    ('"abc"', True, "String with three characters should match"),
    ('"abc def"', True, "String with space character should match"),
    (r'"abc\"def"', True, "String with escaped doublequote in middle should match"),
    ('"abc\"', True, "String with escaped double quote at end should match"),
    ('"abc\\n"', True, "String with escaped newline should match"),
    (r'"abc\\n \\t"', True, "String with escaped tab should match"),
    ('"abc\u0041"', True, "String with escaped hex character should match"),
    ('"abc\u0041def"', True, "String with escaped hex character and following characters should match"),
    ('"abc\u0041defd"', True, "String with escaped hex character, following characters and newline should match"),
]
@pytest.mark.parametrize("test_input, should_match, msg", string_literal_dq_tests)
def test_string_literal_dq(test_input:str, should_match:bool, msg: str) -> None:
    """Test matching of STRING_LITERAL_DQ.
    This is just STRING_LITERAL_DOUBLE_QUOTEABLE surrounded by double quotes, which is tested above.
    STRING_LITERAL_DQ =
    (?:"(?P<string_dq>(?:(?:(?:[\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F])|(?:[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]))|'|(?:\\")|(?:\\(?:(?:[bfnrt/\\])|(?:u(?:(?:(?:[0-9a-cA-C][0-9a-fA-F]{3})|(?:[dD][0-7][0-9a-fA-F]{2})|(?:[eEfF][0-9a-fA-F]{3}))|(?:(?:[dD][89aAbB][0-9a-fA-F]{2})\\u(?:[dD][c-fC-F][0-9a-fA-F]{2})))))))*)")
    """

    pattern_re = re.compile(f"^{bnf.STRING_LITERAL_DQ}$")
    match = pattern_re.match(test_input)
    if should_match:
        assert match is not None, msg
        match_str = match.group("string_dq")
        assert match_str == test_input[1:-1], "Should capture the entire matched string inside quotes as 'string_dq' group"
    else:
        assert match is None, msg


string_literal_sq_tests = [
    ("''", True, "Empty string should match"),
    ('""', False, "Double-quoted empty string should not match"),
    
    ("'la'", True, "String with one character should match"),
    ("'labc'", True, "String with three characters should match"),
    ("'labc def'", True, "String with space character should match"),
    (r"'abc\"def'", False, "String with escaped doublequote in middle should not match"),
    (r"'abc\'def'", True, "String with escaped single quote in middle should match"),
    
    ("'labc\'", True, "String with escaped double quote at end should match"),
    ("'labc\\n'", True, "String with escaped newline should match"),
    (r"'abc\\n \\t'", True, "String with escaped tab should match"),
    ("'labc\u0041'", True, "String with escaped hex character should match"),
    ("'labc\u0041def'", True, "String with escaped hex character and following characters should match"),
    ("'labc\u0041defd'", True, "String with escaped hex character, following characters and newline should match"),
]
@pytest.mark.parametrize("test_input, should_match, msg", string_literal_sq_tests)
def test_string_literal_sq(test_input:str, should_match:bool, msg: str) -> None:
    """Test matching of STRING_LITERAL_SQ.
    This is just STRING_LITERAL_SINGLE_QUOTEABLE surrounded by double quotes, which is tested above.
    STRING_LITERAL_SQ =
    (?:'(?P<string_sq>(?:(?:(?:[\x20\x21\x23-\x26\x28-\x5B\x5D-\x7F])|(?:[\x80-\xFF\u0100-\uD7FF\uE000-\U0010FFFF]))|"|(?:\\')|(?:\\(?:(?:[bfnrt/\\])|(?:u(?:(?:(?:[0-9a-cA-C][0-9a-fA-F]{3})|(?:[dD][0-7][0-9a-fA-F]{2})|(?:[eEfF][0-9a-fA-F]{3}))|(?:(?:[dD][89aAbB][0-9a-fA-F]{2})\\u(?:[dD][c-fC-F][0-9a-fA-F]{2})))))))*)')
    """

    pattern_re = re.compile(f"^{bnf.STRING_LITERAL_SQ}$")
    match = pattern_re.match(test_input)
    if should_match:
        assert match is not None, msg
        match_str = match.group("string_sq")
        assert match_str == test_input[1:-1], "Should capture the entire matched string inside quotes as 'string_sq' group"
    else:
        assert match is None, msg


# Test data for SLICE_SELECTOR
# '(?P<start>(?:0|-?[1-9][0-9]*)[ \t\n\r]*)?
# :
# [ \t\n\r]*?P<end>(?:0|-?[1-9][0-9]*))?[ \t\n\r]*(?:
# :
# [ \t\n\r]*(?P<step>(?:0|-?[1-9][0-9]*))?)?

# pattern=(?:(?P<start>(?:0|-?[1-9][0-9]*))[SPACES]*)?:
slice_selector_tests = [
    (":", True, None, None, None, "One colon and no values should match"),
    ("1:", True, 1, None, None, "One colon and start value should match"),
    ("1:2", True, 1, 2, None, "One colon and start/end values should match"),
    ("1:2:", True, 1, 2, None, "Two colons and start/end values should match"),
    (":2", True, None, 2, None, "One colon and end value should match"),
    (":2:3", True, None, 2, 3, "Two colons and end/step values should match"),
    ("1:2:3", True, 1, 2, 3, "1:2:3 should match"),
    ("::", True, None, None, None, "Two colons and no values should match"),
    ("::-1", True, None, None, -1, "Negative step should match"),
    ("-5 :-1 : -1", True, -5, -1, -1, "Negative start/end/step should match"),
    ("-5 :- 1 : -1", False, -5, -1, -1, "Negative end with space should not match"),
    
    (" : ", False, None, None, None, "No leading spaces"),
    (":  : ", False, None, None, None, "No trailing spaces"),
    (": ", True, None, None, None, "Trailing spaces ok after end if no step"),  # I think this is a loophole in the ABNF
    ("1:     :-1", True, 1, None, -1, "Internal spaces ok"),

]
@pytest.mark.parametrize("test_input, should_match, start, end, step, msg", slice_selector_tests)
def test_slice_selector(test_input:str, should_match:bool, start:int|None, end: int|None, step: int|None,
                        msg: str) -> None:

    re_pattern = re.compile(f"^{bnf.SLICE_SELECTOR}$")
    match = re_pattern.match(test_input)
    if should_match:
        assert match is not None, msg
        assert str(match.group("start")) == str(start), "Start should match"
        assert str(match.group("end"))   == str(end), "End should match"
        assert str(match.group("step"))  == str(step), "Step should match"

    else:
        assert match is None, msg



# Test data for NAME_FIRST
name_first_tests = [
    ('a', True, "ASCII lowercase letter should match"),
    ('Z', True, "ASCII uppercase letter should match"),
    ('_', True, "Underscore should match"),
    ('\u0100', True, "Unicode letter should match"),
    ('\uFFFF', True, "High Unicode character should match"),
    ('\uD800', False, "High surrogate character should not match"),
    ('0', False, "Digit should not match as first character"),
    ('$', False, "Special character should not match"),
    ('ab', False, "Multiple characters should not match - only tests single character")
]
@pytest.mark.parametrize("test_input, should_match, msg", name_first_tests)
def test_name_first(test_input: str, should_match: bool, msg: str ) -> None:
    """Test that NAME_FIRST_RE correctly matches valid first characters of names."""
    pattern_re = re.compile(f"^{bnf.NAME_FIRST}$")
    if should_match:
        assert pattern_re.match(test_input) is not None, msg
    else:
        assert pattern_re.match(test_input) is None, msg

# Test data for NAME_CHAR
name_char_tests = [
    ('a', True, "ASCII lowercase letter should match"),
    ('Z', True, "ASCII uppercase letter should match"),
    ('_', True, "Underscore should match"),
    ('0', True, "Digit should match"),
    ('9', True, "Digit should match"),
    ('\u0100', True, "Unicode letter should match"),
    ('\uFFFF', True, "High Unicode character should match"),
    ('\uD800', False, "High surrogate character should not match"),
    ('$', False, "Special character should not match"),
    ('ab', False, "Multiple characters should not match - only tests single character")
]

@pytest.mark.parametrize("test_input, should_match, msg", name_char_tests)
def test_name_char(test_input: str, should_match: bool, msg: str ) -> None:
    """Test that NAME_CHAR_RE correctly matches valid name characters (after the first character)."""
    pattern_re = re.compile(f"^{bnf.NAME_CHAR}$")
    if should_match:
        assert pattern_re.match(test_input)  is not None, msg
    else:
        assert pattern_re.match(test_input) is None, msg

# Test data for MEMBER_NAME_SHORTHAND
member_name_shorthand_tests = [
    ('a', True, "Single letter should match"),
    ('_', True, "Single underscore should match"),
    ('\u0100', True, "Single Unicode letter should match"),
    ('abc', True, "Multiple ASCII letters should match"),
    ('a123', True, "Letters followed by numbers should match"),
    ('_123', True, "Underscore followed by numbers should match"),
    ('abc_123', True, "Mix of letters, numbers, and underscore should match"),
    ('\u0100abc123', True, "Unicode letter followed by ASCII chars should match"),
    ('123', False, "Starting with digit should not match"),
    ('$abc', False, "Starting with special character should not match"),
    ('', False, "Empty string should not match")
]

@pytest.mark.parametrize("test_input, should_match, msg", member_name_shorthand_tests)
def test_member_name_shorthand(test_input: str, should_match: bool, msg: str ) -> None:
    """Test that MEMBER_NAME_SHORTHAND correctly matches valid member name patterns."""
    pattern_re = re.compile(f"^{bnf.MEMBER_NAME_SHORTHAND}$")
    if should_match:
        assert pattern_re.match(test_input) is not None, (
                msg + f": pattern: {pattern_re.pattern}")
    else:
        assert pattern_re.match(test_input) is None, (
                msg + f": pattern: {pattern_re.pattern}")



# tests_needed = [

#     INDEX_SEGMENT, NAME_SEGMENT,
#     SINGULAR_QUERY_SEGMENTS, ABSOLUTE_SINGULAR_QUERY, RELATIVE_SINGULAR_QUERY, SINGULAR_QUERY, FUNCTION_ARGUMENT.

#
#
# ]
        
        
        
        
# misc helper methods

def char_iter(min: str | int, max: str | int) -> Iterator[str]:
    start = ord(min) if isinstance(min, str) else min
    end   = ord(max) if isinstance(max, str) else max
    for char_ord in range(start, end+1):
        yield chr(char_ord)


def str_digits_generator(ranges: Sequence[tuple[str | int, ...]], repeat: int = 1, step: int = 1) -> Iterator[str]:
    """Generate sequences of digits from the given ranges.
    Each range is a tuple of min (inclusive), max (inclusive) pairs, either as strings or ints.
    If strings, they are first converted to ints via ord(). Then each range is added
    to itertools.chain(), which is passed to itertools.product() with repeat set to the argument value.
    use `step` argument to interate in larger increments.
    """
    iterators: list[Iterator[str]] = []
    for min_max_pair in ranges:
        min_ord = ord(min_max_pair[0]) if isinstance(min_max_pair[0], str) else min_max_pair[0]
        max_ord = ord(min_max_pair[1]) if isinstance(min_max_pair[1], str) else min_max_pair[1]
        iterators.append(char_iter(min_ord, max_ord))
    
    product_list = list( itertools.product( itertools.chain(*iterators), repeat=repeat ))
    for index in range(0, len(product_list), step):
        yield ''.join(product_list[index])   # concatenate the digits into a single str