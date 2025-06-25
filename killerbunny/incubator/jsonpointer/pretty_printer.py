from typing import NamedTuple

from killerbunny.incubator.jsonpointer.constants import JSON_SCALARS, SCALAR_TYPES, JSON_VALUES, OPEN_BRACE, \
    CLOSE_BRACE, \
    SPACE, COMMA, EMPTY_STRING, CLOSE_BRACKET, OPEN_BRACKET

# todo recursive code for printing list and dict members needs to detect cycles and have a maximum recursion depth
class FormatFlags(NamedTuple):
    """Flags for various pretty printing options for Python nested JSON objects.

    Standard defaults designed for debugging small nested dicts, and as_json_format() is useful for initializing
    flags for printing in a json compatible format.

    The various "with_xxx()" methods make a copy of this instance's flags and allow you to set a specific flag.
    """
    quote_strings: bool = False  # when True wrap strings in quotes, when False omits quotes
    single_quotes: bool = False  # when True use single quotes instead of double quotes
    use_repr:      bool = False  # when True format strings with str() instead of repr()
    format_json:   bool = False  # when True use "null" for "None" and "true" and "false" for True and False
    indent:        int = 2       # number of spaces to indent each level of nesting
    single_line:   bool = True   # when True format output as single line, when False over multiple lines
    # when True do not insert commas after list and dict item elements
    # note: when printing with single_line = True, if omit_commas is also True, output may be confusing
    # as list and dict elements will have no obvious visual separation in the string, and parsing will be difficult
    omit_commas:   bool = False  # when True do not insert commas after list and dict item elements

    @staticmethod
    def as_json_format() ->"FormatFlags":
        # is this sufficient to make a JSON formatted string?
        #  todo - investigate RFC for encoding JSON strings from python objects
        #  (technically a serialization format but I think it's called Decoding in the JSON pacakge)
        return FormatFlags(quote_strings=True, single_quotes=False,  use_repr=True, format_json=True, indent=2,
                           single_line=False, omit_commas=False)

    def with_indent(self, indent: int) -> "FormatFlags":
        return FormatFlags(quote_strings=self.quote_strings, single_quotes=self.single_quotes,
                           use_repr=self.use_repr, format_json=self.format_json, indent=indent,
                           single_line=self.single_line, omit_commas=self.omit_commas)

    def with_quote_strings(self, quote_strings: bool) -> "FormatFlags":
        return FormatFlags(quote_strings=quote_strings, single_quotes=self.single_quotes,  use_repr=self.use_repr,
                           format_json=self.format_json, indent=self.indent, single_line=self.single_line, omit_commas=self.omit_commas)

    def with_single_quotes(self, single_quotes: bool) -> "FormatFlags":
        return FormatFlags(quote_strings=self.quote_strings, single_quotes=single_quotes,  use_repr=self.use_repr,
                           format_json=self.format_json, indent=self.indent, single_line=self.single_line, omit_commas=self.omit_commas)

    def with_use_repr(self, use_repr: bool) -> "FormatFlags":
        return FormatFlags(quote_strings=self.quote_strings, single_quotes=self.single_quotes,  use_repr=use_repr,
                           format_json=self.format_json, indent=self.indent, single_line=self.single_line, omit_commas=self.omit_commas)

    def with_format_json(self, format_json: bool) -> "FormatFlags":
        return FormatFlags(quote_strings=self.quote_strings, single_quotes=self.single_quotes,
                           use_repr=self.use_repr, format_json=format_json, indent=self.indent,
                           single_line=self.single_line, omit_commas=self.omit_commas)

    def with_single_line(self, single_line: bool) -> "FormatFlags":
        """Copy existing flags and set single_line flag to argument value.

        Note: if single_line is True, this method also sets omit_commas to False as a sensible default.
        """
        _omit_commas = False if single_line else self.omit_commas
        return FormatFlags(quote_strings=self.quote_strings, single_quotes=self.single_quotes, use_repr=self.use_repr, format_json=self.format_json,
                           indent=self.indent, single_line=single_line, omit_commas=_omit_commas)

    def with_omit_commas(self, omit_commas: bool) -> "FormatFlags":
        return FormatFlags(quote_strings=self.quote_strings, single_quotes=self.single_quotes,
                           use_repr=self.use_repr, format_json=self.format_json, indent=self.indent,
                           single_line=self.single_line, omit_commas=omit_commas)


def format_scalar(scalar_obj: JSON_SCALARS, format_: FormatFlags) -> str:
    """Format the scalar_obj according to the Format flags.
    If the scalar_obj is None, returns None, or "null" if format_json is True
    If the scalar_obj is a bool, returns True/False, or "true"/"false" if format_json is True
    Otherwise, return str(scalar_obj), or repr(scalar_obj) if use_repr is True
    If quote_strings is True, enclose str objects in quotes (single or double as specified by format_.single_quotes))

    FormatFlags :
        format_.quote_strings: If True, enclose str objects in  quotes, no quotes if False
        format_.single_quotes: If True, use single quotes instead of double quotes when quoting strings
        format_.use_repr: If True, use repr() to format the scalar object, otherwise use str()
        format_json: If True, return None and bool objects as JSON literal values null, true, false
        format_.indent: number of spaces to indent each level of nesting
        format_.single_line: when True format output as single line, when False over multiple lines
        format_.omit_commas: when True do not insert commas after list and dict item elements



    :param scalar_obj: the scalar object to format
    :param format_: Formatting flags used to specify formatting options

    :return: the formatted object as a string, or 'None'/'null' if scalar_obj argument is None
    """
    # no quotes used around JSON null, true, false literals
    if scalar_obj is None:
        return 'null' if format_.format_json else 'None'
    if isinstance(scalar_obj, bool):
        if format_.format_json:
            return "true" if scalar_obj else "false"
        else:
            return str(scalar_obj)  # str() and repr() return same string for bool

    quote_char = "'" if format_.single_quotes else '"'

    if format_.use_repr:
        s = repr(scalar_obj)
        if isinstance(scalar_obj, str):
            # repr adds single quotes around the string, which we do not want.
            s = s[1:-1]
            # repr doesn't always escape a double quote in a str!
            #   E.g.: repr() returns 'k"l' for "k"l", instead of "k\"l" which makes the JSON decoder fail.  Frustrating!
            # todo investigate rules for valid JSON strings and issues with repr()
            s = s.replace('"', '\\"')  # todo do we need a regex for this to only replace " not preceeded by a \ ?
    else:
        s = str(scalar_obj)
    if isinstance(scalar_obj, str) and format_.quote_strings:
        return f'{quote_char}{s}{quote_char}'
    return s


def _spacer(format_: FormatFlags, level: int) -> str:
    if format_.single_line:
        return SPACE
    return SPACE * ( format_.indent * level )

def _is_empty_or_single_item(obj: JSON_VALUES ) -> bool:
    """Recurse the list or dict and return true if every nested element is either empty,
    or contains exactly one scalar list element or one key/value pair where value is a single scalar value.
    Another way to think of this is, if the structure does not require a comma, this method will return True
    E.g.
    [ [ [ ] ] ] ,  [ [ [ "one" ] ] ]  - both return True
    { "key: "one" },  { "key": [ [ "one"  ] ] } - both return True
    [ [ { "key": [ [ "foo"  ] ] } ] ]  - returns True
    { "key1": { "key2": { "key3": "foo }}} - returns True
    [ [ [ "one", "two" ] ] ] - returns False
    { "key": [ [ "one", "two"  ] ] }  - returns False
    { "key": [ [ { "one":"foo", "two":"bar" } ] ] } - returns False
    """
    #base case:
    if isinstance(obj, SCALAR_TYPES):
        return True
    if isinstance(obj, (list, dict)) and len(obj) == 0:
        return True
    if isinstance(obj, (dict, list)) and len(obj) > 1:
        return False
    elif isinstance(obj, list) and len(obj) == 1:
        return _is_empty_or_single_item(obj[0])
    elif isinstance(obj, dict) and len(obj) == 1:
        return _is_empty_or_single_item(next(iter(obj.values())))
    else:
        return False

def _pp_dict(json_dict: dict[str, JSON_VALUES], format_: FormatFlags, lines: list[str], level: int = 0) -> list[str]:
    if not isinstance(json_dict, dict):
        raise TypeError(f"Encountered non dict type: {type(json_dict)}")
    if len(lines) == 0:
        lines.append("")

    if lines[-1] != EMPTY_STRING:
        indent_str = SPACE * ( format_.indent - 1)  # current line already has text, so indent is relative to end of that text
    elif len(lines) == 1 or level == 0:
        indent_str = EMPTY_STRING
    else:
        indent_str = _spacer(format_, level)

    if len(json_dict) == 0:
        lines[-1] += f"{indent_str}{OPEN_BRACE}{SPACE}{CLOSE_BRACE}"
        return lines
    if len(json_dict) == 1:
        k, v = next(iter(json_dict.items()))
        if isinstance(v, SCALAR_TYPES):
            kf = format_scalar(k, format_)
            vf = format_scalar(v, format_)
            lines[-1] += f"{indent_str}{OPEN_BRACE}{SPACE}{kf}:{SPACE}{vf}{SPACE}{CLOSE_BRACE}"
            return lines

    comma = EMPTY_STRING if format_.omit_commas else COMMA
    sp   = SPACE if format_.single_line else EMPTY_STRING
    lines[-1] += f"{indent_str}{OPEN_BRACE}"  # start of dict text : {

    level += 1
    indent_str = _spacer(format_, level)
    for index, (key, value) in enumerate(json_dict.items()):

        # deal with commas
        first_item: bool = (index == 0)
        last_item:  bool = (index == (len(json_dict) - 1 ))  # no comma after last item

        kf = format_scalar(key, format_)  # formatted key
        if isinstance(value, SCALAR_TYPES):
            lines.append("")
            vf = format_scalar(value, format_)
            lines[-1] = f"{indent_str}{kf}:{SPACE}{vf}"
        elif isinstance(value, list):
            lines.append("")
            lines[-1] = f"{indent_str}{kf}:"
            # special case is where value is either an empty list or a list with one scalar element:
            # we can display this value on the same line as the key name.
            if len(value) > 1:
                lines.append("")
            elif len(value) == 1:
                # if there is only one single element or key/value pair, we print it on the same line.
                if _is_empty_or_single_item(value):
                   #lines[-1] += SPACE
                    ...
                else:
                    lines.append("")
            _pp_list(value, format_, lines, level)
        elif isinstance(value, dict):
            lines.append("")
            lines[-1] = f"{indent_str}{kf}:"
            # special case is where value is either an empty dict or a dict with one key with a scalar value:
            # we can display the nested dict on the same line as the key name of the parent dict.
            if len(value) > 1:
                lines.append("")
            elif len(value) == 1:
                nk, nv = next(iter(value.items()))
                if not isinstance(nv, SCALAR_TYPES):
                    lines.append("")
            _pp_dict(value, format_, lines, level)

        if not last_item:
            lines[-1] +=  comma


    if _is_empty_or_single_item(json_dict):
        # this was a single item dict, so display closing brace on same line
        lines[-1] += f"{SPACE}{CLOSE_BRACE}"
    else:
        level -= 1
        indent_str = sp if format_.single_line else _spacer(format_, level)
        lines.append(f"{indent_str}{CLOSE_BRACE}")


    return lines


def _pp_list(json_list: list[JSON_VALUES], format_: FormatFlags, lines: list[str], level: int = 0) -> list[str]:

    if not isinstance(json_list, list):
        raise TypeError(f"Encountered non list type: {type(json_list)}")

    if len(lines) == 0:
        lines.append("")

    if lines[-1] != EMPTY_STRING:
        indent_str = SPACE * ( format_.indent - 1)  # current line already has text, so indent is relative to end of that text
    elif len(lines) == 1 or level == 0:
        indent_str = EMPTY_STRING
    else:
        indent_str = _spacer(format_, level)

    if len(json_list) == 0:
        lines[-1] += f"{indent_str}{OPEN_BRACKET}{SPACE}{CLOSE_BRACKET}"
        return lines
    if len(json_list) == 1 and isinstance(json_list[0], SCALAR_TYPES):
        s = format_scalar(json_list[0], format_)
        lines[-1] += f"{indent_str}{OPEN_BRACKET}{SPACE}{s}{SPACE}{CLOSE_BRACKET}"
        return lines

    comma = EMPTY_STRING if format_.omit_commas else COMMA
    sp   = SPACE if format_.single_line else EMPTY_STRING
    lines[-1] += f"{indent_str}{OPEN_BRACKET}"

    level += 1
    indent_str = _spacer(format_, level)
    for index, item in enumerate(json_list):

        first_item: bool = (index == 0)
        last_item:  bool = (index == (len(json_list) - 1 ))  # no comma after last element

        if isinstance(item, SCALAR_TYPES):
            lines.append("")
            s = format_scalar(item, format_)
            lines[-1] = f"{indent_str}{s}"
        elif isinstance(item, list):
            if not first_item:  # if this is a new list starting inside of list, open brackets can go on same line
                lines.append("")
            _pp_list(item, format_, lines, level)
        elif isinstance(item, dict):
            if not first_item:  # if this is a new dict starting inside of list, open brackets can go on same line
                lines.append("")
            _pp_dict(item, format_, lines, level)

        if not last_item:
            lines[-1] +=  comma

    if _is_empty_or_single_item(json_list):
        # this was a single element line, so display closing bracket on same line
        lines[-1] += f"{SPACE}{CLOSE_BRACKET}"
    else:
        level -= 1
        indent_str = sp if format_.single_line else _spacer(format_, level)
        lines.append(f"{indent_str}{CLOSE_BRACKET}")

    return lines

def pretty_print(json_obj: JSON_VALUES, format_: FormatFlags, lines: list[str], indent_level: int = 0) -> str:
    """Return the JSON value formatted as a str according to the flags in the format_ argument.

    Typically, an empty list is passed to this method. Each generated line of formatted outut is appended
    to the lines list argument.
    When this method returns, the lines argument will contain each line in the formatted str, or a single new
    element if format_.single_line is True. These lines are then joined() and returned.

    """

    lines.append("")  # so format methods will have a new starting line for output
    if isinstance(json_obj, SCALAR_TYPES):
        lines[-1] = format_scalar(json_obj, format_)
    elif isinstance(json_obj, list):
        _pp_list(json_obj, format_, lines, indent_level)
    elif isinstance(json_obj, dict):
        _pp_dict(json_obj, format_, lines, indent_level)
    else:
        raise ValueError(f"Unsupported type: {type(json_obj)}")

    if format_.single_line:
        return "".join(lines)
    else:
        return "\n".join(lines)

