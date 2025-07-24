import re

JSON_FILE_SUFFIX = ".json"
PATH_VALUES_SUFFIX = ".path_values"
JPATH_VALUES_SUFFIX = ".jpath_values"

ONE_MEBIBYTE = 1*1024*1024
UTF8 = "utf-8"

_SOLIDUS = chr(0x2F)  # i.e., forward slash '/'
# Per RFC4627 all these must be escaped in a JSON string:
_REVERSE_SOLIDUS: str = chr(0x5C)  # backspace '\'
_QUOTATION_MARK: str =  chr(0x22)  # double quotes '"'
_CONTROL_CHARS: set[str]  = { chr(cntl) for cntl in range(0x00, 0x20) }
_ESCAPE_REQUIRED: set[str] = set().union(_REVERSE_SOLIDUS, _QUOTATION_MARK, *_CONTROL_CHARS)


_ESCAPE_CHAR = _REVERSE_SOLIDUS
_ESCAPED_REVERSE_SOLIDUS = _ESCAPE_CHAR + _REVERSE_SOLIDUS

# forward slashes (U+002F,%x2F) in identier names (i.e. dict key names) are represented this way
_ESCAPED_SOLIDUS = '~1'  # unescape to -> /
# tilde (U+007E,%x7E) characters in identifier names are represented this way:
_ESCAPED_TILDE   = '~0'  # unescape to -> ~

_TOKEN_SEPARATOR = _SOLIDUS  # forward slash '/'
# Empty string used as root, i.e. the entire object. '/' refers to a dict key named "" (empty string).
# If no such key exists, it's an error state.
# Because why stick with 50-year-old, well-known standards when you can invent new ones, right RFC6901? :-(
EMPTY_STRING = ""
ROOT_PATH = EMPTY_STRING
ROOT_PATH_DISPLAY_STR = '""'
END_OF_ARRAY_TOKEN = "-"

PATH_VALUE_SEPARATOR = "  :  "

OPEN_BRACE    = '{'
CLOSE_BRACE   = '}'
OPEN_BRACKET  = '['
CLOSE_BRACKET = ']'
SPACE = ' '
COMMA = ','


#----------------------------------------------------------------------------------------------------
# RE PATTERNS
#----------------------------------------------------------------------------------------------------

_SOLIDUS_RE = re.compile(_SOLIDUS)
_REVERSE_SOLIDUS_RE = re.compile(_ESCAPED_REVERSE_SOLIDUS)
_QUOTATION_MARK_RE = re.compile(_QUOTATION_MARK)
_ARRAY_INDEX_RE = re.compile(r"^0|[1-9][0-9]*|-")  # array index is 0, any int with no leading zeros, or a hypen '-'


