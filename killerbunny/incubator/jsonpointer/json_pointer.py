"""Testing implementation of a json pointer"""
import re
from typing import Any

from killerbunny.incubator.jsonpointer.constants import _ESCAPED_SOLIDUS, \
    _ESCAPED_TILDE, _TOKEN_SEPARATOR, EMPTY_STRING, END_OF_ARRAY_TOKEN, _ARRAY_INDEX_RE
from killerbunny.shared.json_type_defs import JSON_PRIMITIVE_TYPES, JSON_ValueType

"""
To represent a json object as a string, you must escape the json dict_ - specifically the strings in the json dict_
q: Key names only? Or values like key values, list values? 
To represent a json string as a json dict_, you must unescape the string - as in deserializing text in a json file 
which is a string representing a json dict_/python dict
"""


def validate(json_obj: JSON_ValueType, pointer_str: str, ) -> bool:
    """Return True if valid JSON Pointer str, otherwise return False

    It turns out, you cannot pre-validate a pointer. Its correctness is context-sensitive. It depends on the object
    to which it refers. For example, a reference-token like "000123" would be valid as a key name in a dict but invalid
    as the index of an array. Without the json object to compare to, you cannot determine if "000123" is valid or not.
    """
    try:
        _ = resolve_json_pointer(json_obj, pointer_str)
        return True  # invalid pointers raise an exception
    except (ValueError, IndexError, KeyError) as _:
        return False


def unescape_ref_token(escaped_ref_token: str) -> str:
    """Reference tokens are unescaped when being evaluated, otherwise they are escaped"""
    unescaped_ref_token = re.sub(_ESCAPED_SOLIDUS, '/', escaped_ref_token)
    unescaped_ref_token = re.sub(_ESCAPED_TILDE, '~', unescaped_ref_token)
    return unescaped_ref_token

def escape_ref_token(unescaped_ref_token: str) -> str:
    """Reference tokens are escaped unless being evaluated. """
    #print(f"{unescaped_ref_token=}")
    escaped_ref_token = re.sub('~', _ESCAPED_TILDE, unescaped_ref_token)
    #print(f"{escaped_ref_token=}")
    escaped_ref_token = re.sub('/', _ESCAPED_SOLIDUS, escaped_ref_token)
   # print(f"{escaped_ref_token=}")
    return escaped_ref_token


def path_components(path: str) -> list[str]:
    ref_tokens = path.split(_TOKEN_SEPARATOR)
    return ref_tokens


def subpath(path: list[str] | str, path_component_index:int = -1) -> str:
    """Return the subpath composed of first N reference tokens, where N == path_component_index argument.
    If path_component_index == -1. return the full path.
    """
    reference_tokens = path
    if isinstance(path, str):
        reference_tokens = path_components(path)
    return _TOKEN_SEPARATOR.join(token for token in reference_tokens[:path_component_index+1])

"""
todo - error handling. We could have different modes of operation, e.g
STRICT - raise exceptions when path is invalid or referes to non-existent data member
LENIENT - don't throw exceptions but return None instead
DEV - return  falsie elements "", 0, [], or {}  
"""

def resolve_json_pointer(json_obj: JSON_ValueType, path: str) -> Any:
    """Return the value referenced by the json_pointer path."""
    if path == EMPTY_STRING:
        return json_obj
    if path == _TOKEN_SEPARATOR and not ( isinstance(json_obj, dict) and  json_obj.get("", None) is not  None):
        # Special case if a top-level dict happens to have a key named "" (empty string). Must treat / as reference to
        # that key's value and not the entire object. Per RFC6901. Also, without this check, there would be no way to
        # address this dict key
        return json_obj
    cur_node = json_obj
    ref_tokens = path_components(path)
    last_path_index = len(ref_tokens) - 1
    #print(f"ref_tokens = {ref_tokens}")
    for index, ref_token in enumerate(ref_tokens):
        if index == 0 and ref_token == EMPTY_STRING:
            continue  # first token in list of len > 1, this is just the root dict_ ref, so skip
        # per RFC6901
        unesc_path = unescape_ref_token(ref_token)
        if isinstance(cur_node, dict):
            if unesc_path not in cur_node:
                raise KeyError(f"Invalid dict key '{unesc_path}' in path '{subpath(ref_tokens,index)}'")
            cur_node = cur_node[unesc_path]
        elif isinstance(cur_node, list):
            # per RFC6901 the END_OF_ARRAY_TOKEN references past the end of an array, so it's not a valid index value.
            # (so why does this exist??) "Thus, applications of the JSON Pointer need to specify how that character is
            # to be handled, if it is to be useful. Temp use : return the length of the array.
            # todo - longer term, what does array[-] mean???
            list_length = len(cur_node)
            if unesc_path == END_OF_ARRAY_TOKEN:
                cur_node = list_length
            else:
                i: int = 0
                # Per RFC7901 section 4, array indexes cannot have leading zeros
                if not _ARRAY_INDEX_RE.fullmatch(unesc_path):
                    zero_msg = ""
                    if unesc_path.startswith('0'):
                        zero_msg = f". Leading zeros are not allowed in list indexes."
                    raise IndexError(f"Invalid list index format '{unesc_path}' in path "
                                     f"'{subpath(ref_tokens,index)}'{zero_msg}")
                try:
                    i = int(unesc_path)
                    if  i >= list_length or i < 0:
                        raise IndexError(f"Invalid list index {i} in path "
                                         f"'{subpath(ref_tokens,index)}' for list of length {list_length}")
                    cur_node = cur_node[int(unesc_path)]
                except ValueError:
                    # raise ... from None prevents chaining the ValueError from the int(unsec_path), which we are handling here
                    raise ValueError(f"Invalid list index type:{type(unesc_path).__name__} in path "
                                     f"'{subpath(ref_tokens,index)}'") from None

        elif isinstance(cur_node, JSON_PRIMITIVE_TYPES):
            # terminal node, should align with end of path
            # todo error handling if more path components left to process
            if index != last_path_index:
                raise ValueError(f"Invalid path reference '{subpath(ref_tokens,index+1)}', last good value: '{cur_node}' for path '{subpath(ref_tokens,index)}'")
        else:
            raise TypeError(f"Encountered non JSON type: {type(cur_node)}")
        #print(f"index is {index} and {unesc_path=}, {cur_node=}")
        if isinstance(cur_node, JSON_PRIMITIVE_TYPES) and index != last_path_index:
            #print(f"*********** TERMINAL NODE REACHED, BUT PATH CONTINUES *****")
            raise ValueError(f"Invalid path reference '{subpath(ref_tokens,index+1)}', last good value: '{cur_node}' "
                             f"for path '{subpath(ref_tokens,index)}'")

    #print(f"resolve_json_pointer: path = {path}")
    return cur_node
