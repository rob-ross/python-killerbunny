from common.screen_utils import hex_and_chars


def t_str_vs_repr() -> None:
    """This is for a how-to guide. Shows the difference between str() and repr() for different str literals.

    repr(), !r, __repr__ is useful for development and debugging. It returns a string that if evaluated as Python
    code would recreate the object.
    str(), !s, __str__ human-readable representation of the object contents. For a str has fidelity with actual image in memory
    See below,

    """
    s = 'k"l'  # using single quotes on outside escapes the double quote inside
    print(f"repr: {repr(s)}, str: {s}")
    # "k"l" is an invalid string literal because the middle quote matches the first, and l" is a syntax error
    #   s = "k"l" <-- syntax error
    s = "k\"l"  # double quotes on outside, so must escape the double quote inside. Produces same str as 'k"l' above
    print(f"repr: {repr(s)}, str: {s}")
    s = r"k\"l"
    print(f"repr: {repr(s)}, str: {s}")
    s = 'k\"l'  # \" is escape sequence for ", but is redundant here because we're using outer single quotes
    print(f"repr: {repr(s)}, str: {s}")

    """ 
    output:
    
        repr: 'k"l', str: k"l
        repr: 'k"l', str: k"l
        repr: 'k\\"l', str: k\"l
        repr: 'k"l', str: k"l

    
    """
    print()

    # \j is not an escape sequence so backslash treated as a literal.
    # Also results in  SyntaxWarning: invalid escape sequence '\j'
    s = 'i\j'
    print(f"repr: {repr(s)}, str: {s}")
    s = r'i\j'
    print(f"repr: {repr(s)}, str: {s}")
    s = "i\\j" # \\ is an escaped backslash sequence, treated as single backslash. This is the correct syntax.
    print(f"repr: {repr(s)}, str: {s}")
    s = r"i\\j"  # raw \\ treated like two literal backslashes so repr() escapes each backslash
    print(f"repr: {repr(s)}, str: {s}")

    """
    output:
    
        repr: 'i\\j', str: i\j
        repr: 'i\\j', str: i\j
        repr: 'i\\j', str: i\j
        repr: 'i\\\\j', str: i\\j

    """
    print()

    s = '\n' #  valid escape sequence. Here, the backlash is not part of the character, it encodes the special newline char
             # This is not a literal '\n' sequence. If you wanted that, you need to escape the backslash like:
                # '\\n' # literal backlash char followed by an 'n'.

def double_quote_repr(s: str) -> str:
    return f'"{s.replace(chr(34), r"\"")}"'


def backslash_with_no_escape_sequence() -> None:
    print()
    # s:str = "\x"  # start of a unicode escape sequence, but syntax error because missing hex digits
    s:str = "\x61" # valid escape sequence. Here, the backlash is not part of the character, it encodes the special newline char
    print(f"backslash-x-61: repr: {repr(s)}, str: {s}")
    
    s = "\\x61"  # escaped the backslash, so it will be treated as a literal backslash
    print(f"backslash-backslash-x-61: repr: {repr(s)}, str: {s}")
    
    s = r"\x61"  # raw \x61 will be treated as a literal backslash
    print(f"raw backslash-x-61: repr: {repr(s)}, str: {s}")
    
    s = "\n\t\r\v"
    print(hex_and_chars(s))
    print(f"raw backslash-x-61: repr: {repr(s)}, str: {s}")

    # interesting rule: You can't have an odd number of backlashes at the end of a raw string literal.
    #s = r"\" # doesn't work, because the backslash escapes the closing quote and results in an unterminated string
    #s = "\"  # not allowed for same reason as above. This is a design quirk of Python's raw string literals.
    s = r"\"" # this is allowed. string is a literal backslash followed by a double quote.
    print(f"raw backslash-doublequote: repr: {repr(s)}, str: {s}")
    
    s = r"\\" # two literal backslashes. Raw strings can't end with an odd number of backslashes.
    print(f"raw backslash-backslash: repr: {repr(s)}, str: {s}")
    s = "\\" # this results in a single literal backslash.
    print(f"backslash-backslash: repr: {repr(s)}, str: {s}")
    #s = "\\\" # final double quote is escaped, unterminated string
    s = r"\\\foo"  # odd number of literal backslashes allowed anywhere but very end of raw string literal.
    print(f"raw backslash-backslash-backslash: repr: {repr(s)}, str: {s}")

    # fr or rf?
    thing = 1
    s = fr"\b{thing}"
    print(f"f raw backslash-b-{{thing}}: repr: {repr(s)}, str: {s}")
    s = rf"\b{thing}"
    print(f"r f backslash-b-{{thing}}: repr: {repr(s)}, str: {s}")

    s = 'this is \s'
    #return f'\\{s}'

def t_encoded_literals() -> None:
    print()
    s = "\x5c" # hex escape sequence for \
    # this allows a single literal backslash to be entered in a string literal.
    print(f"repr: {repr(s)}, str: {s}")
    
    s = '\x5c\x5c'  # two literal backslashes characters
    print(f"repr: {repr(s)}, str: {s}")
    print(hex_and_chars(s))
    
    print()
    s = '\u005c' # unicode escape sequence for \
    print(f"repr: {repr(s)}, str: {s}")
    
    s = '\u005c\u005c'  # two unicode escape sequences for \
    print(f"repr: {repr(s)}, str: {s}")
    print(hex_and_chars(s))
    print()
    s = '\U0000005c'
    print(f"repr: {repr(s)}, str: {s}")
    
    s = '\U0000005c\U0000005c'
    print(f"repr: {repr(s)}, str: {s}")
    
    
    # do raw strings change the behavior?
    s = r'\x5c'  # raw string here escapes the backslash, so it will be treated as a literal backslash followed by
    # literal x, 5, then c.
    print(f"repr: {repr(s)}, str: {s}")
    print(hex_and_chars(s))
    print()
    s = r'\u005c'  # raw strings makes this a literal backslash, u, zero, zero, five, c.
    print(f"repr: {repr(s)}, str: {s}")
    print(hex_and_chars(s))
if __name__ == '__main__':
    #t_str_vs_repr()
    s = double_quote_repr('k"l')
    print(s)
    
    #backslash_with_no_escape_sequence()
    
    t_encoded_literals()
