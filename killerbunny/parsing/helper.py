#  File: helper.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#
import logging
import re

from killerbunny.shared.jpath_bnf import JPathBNFConstants as bnf

_logger = logging.getLogger(__name__)


# This map is for single-character escapes after the backslash
# see 2.3.1.2. Semantics, Table 4 "Escape Sequence Replacements", pg 18, RFC 9535

_UNESCAPE_MAP = {
    'b': '\b',
    't': '\t',
    'n': '\n',
    'f': '\f',
    'r': '\r',
    '"': '"',
    "'": "'",  # For JSONPath's \', though not in standard JSON Table 4
    '/': '/',
    '\\': '\\',
}
# This regex captures the part *after* the backslash:
# - uXXXX (e.g., u0041)
# - or a single character from our map (e.g   b, t, n, f, r, ", ', /, \ )
_ESCAPE_SEQUENCE_RE = re.compile(r'\\(u[0-9a-fA-F]{4}|[btnfr"\'/\\])')


# Modify the bnf regex to exclude escaping single quotes if already escaped
# This regex also excludes the [' and '] patterns
_NORMAL_ESCAPABLE_RE = re.compile(
    r'[\\\b\f\n\r\t]|'
    r'(?<!\\)(?<!\[)\'(?!\])'  # Single quote not escaped, not part of [' or ']
)



_ESCAPE_MAP = {
    '\b' : r'\b',
    '\t' : r'\t',
    '\n' : r'\n',
    '\f' : r'\f',
    '\r' : r'\r',
    "'"  : r"\'",
    bnf.BACKSLASH: bnf.BACKSLASH_ESC,
}

# _UNESCAPE_SEQUENCE_RE = re.compile( r"([\b\t\n\f\r'\\])" )

def _escape_char_for_jsonpath(match_obj: re.Match[str]) -> str:
    # todo escape unicode references properly
    unescaped_char = match_obj.group(0)
    if len(unescaped_char) == 1 and unescaped_char in _ESCAPE_MAP: # Check for characters that need escaping
        return _ESCAPE_MAP[unescaped_char]
    
    _logger.warning(f"Unknown character encountered by escaper: {match_obj.group(0)}")
    print(f"Unknown character encountered by escaper: {match_obj.group(0)}")

    return match_obj.group(0)

def escape_string_content(content: str) -> str:
    # todo what do we do about escaping this part of the bnf.NORMAL_ESCAPABLE: |(?:u{NORMAL_HEXCHAR}) ?
    return _NORMAL_ESCAPABLE_RE.sub(_escape_char_for_jsonpath, content)



def _unescape_char_for_jsonpath(match_obj: re.Match[str]) -> str:
    """Replacement function for re.sub to unescape a matched sequence.
    see section 2.3.1.2., pg 18 in RFC 9535
    """
    escaped_part = match_obj.group(1)  # The part after the backslash
    
    if escaped_part.startswith('u'):  # Check if it's uXXXX
        hex_code = escaped_part[1:]
        # Ensure it's exactly 4 hex digits (regex already does, but good practice)
        if len(hex_code) == 4:
            try:
                return chr(int(hex_code, 16))
            except ValueError as ve:
                # Invalid hex sequence, should ideally not happen if regex is tight
                # and lexer is correct. Return original match to be safe or log error.
                _logger.warning(f"Invalid Unicode escape sequence: \\{escaped_part}")
                print(f"{ve}; Invalid Unicode escape sequence: \\{escaped_part}")
                return match_obj.group(0) # Return the full original escape sequence (e.g., \uDEFG)
    elif len(escaped_part) == 1 and escaped_part in _UNESCAPE_MAP: # Check for single char escapes
        return _UNESCAPE_MAP[escaped_part]
    
    # If it's an escape sequence matched by the regex but not handled above
    # (shouldn't happen with the current regex and map), return original.
    # Or, if the regex was broader (e.g., \\.), this would handle unknown escapes.
    _logger.warning(f"Unknown escape sequence encountered by unescaper: {match_obj.group(0)}")
    return match_obj.group(0)

def unescape_string_content(content: str) -> str:
    """Unescape JSONPath string content with proper surrogate pair handling."""
    # First pass: find and convert surrogate pairs
    surrogate_pair_re = re.compile(r'\\u([Dd][89AaBb][0-9a-fA-F]{2})\\u([Dd][c-fC-F][0-9a-fA-F]{2})')
    
    def replace_surrogate_pair( match: re.Match[str] ) -> str:
        high = int(match.group(1), 16)
        low = int(match.group(2), 16)
        # Calculate actual code point from surrogate pair
        code_point = ((high - 0xD800) << 10) + (low - 0xDC00) + 0x10000
        return chr(code_point)
    
    # Replace surrogate pairs first
    content = surrogate_pair_re.sub(replace_surrogate_pair, content)
    
    # Then handle all other escape sequences
    return _ESCAPE_SEQUENCE_RE.sub(_unescape_char_for_jsonpath, content)



def unescape_string_content_prev(content: str) -> str:
    """Unescape JSONPath string content.
    'content' is the string *without* its surrounding quotes.
    """
    return _ESCAPE_SEQUENCE_RE.sub(_unescape_char_for_jsonpath, content)
