#  File: value_nodes.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

"""
These are nodes used to return query results from the evaluator. They are distinct from the "Nodes" used by the AST.
"""
import json
import logging
from typing import Iterator, Generator, override

from killerbunny.evaluating.evaluator_types import EvaluatorValue, NormalizedJPath
from killerbunny.parsing.helper import unescape_string_content
from killerbunny.shared.json_type_defs import JSON_ValueType

_logger = logging.getLogger(__name__)


class VNode:
    """This class holds a normalized JSON Path and the JSON object to which it refers. This class is intended to be
    immutable. However, the underlying JSON value may be mutable, such as with arrays(lists) or objects (dicts).
    Although this class overrides __hash__, because it overrides __eq__, lists and dicts are not hashable, and calling
    __hash__ on instances with these types will raise a TypeError. Thus, VNode as-is is not designed to be used as
    a hash map key.
    
    todo - we need to store the root value, and the node depth (root node = 0) for path processing.
    i.e., _root_value, _node_depth
    
    """
    def __init__(self,
                 jpath: NormalizedJPath,
                 json_value: JSON_ValueType,
                 root_value: JSON_ValueType,
                 node_depth: int) -> None:
        super().__init__()
        self._jpath: NormalizedJPath = jpath
        self._json_value: JSON_ValueType = json_value
        self._root_value: JSON_ValueType = root_value
        self._node_depth: int = node_depth
        
    @property
    def jpath(self) -> NormalizedJPath:
        """ Return the NormalizedJPath instance wrapping the json path query string.
        todo - serach for uses of foo.jpath.jpath_str and change to foo.jpath_str
        """
        return self._jpath
    
    @property
    def jpath_str(self) -> str:
        """ Return the str representation of the NormalizedJPath instance """
        return self._jpath.jpath_str
    
    @property
    def jvalue(self) -> JSON_ValueType:
        return self._json_value
    
    @property
    def root_value(self) -> JSON_ValueType:
        return self._root_value
    
    @property
    def node_depth(self) -> int:
        return self._node_depth
    
    def __repr__(self) -> str:
        repr_str = f"VNode(jpath={self._jpath}, json_value={repr(self._json_value)})"
        return repr_str
    
    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VNode):
            return NotImplemented
        other_vnode:VNode = other
        return self._jpath == other_vnode._jpath and self._json_value == other_vnode._json_value

    @override
    def __hash__(self) -> int:
        # The hash depends on the hash of _jpath and _json_value.
        # JSON_ValueType can contain lists or dicts, which are unhashable.
        # If _json_value can be an unhashable type (like a list or dict),
        # VNode instances themselves will be unhashable.
        # This is generally fine if we don't need to put VNodes in sets/dict keys.
        # If we *do* need them to be hashable and _json_value can be unhashable,
        # we'd need a strategy (e.g., converting lists to tuples for hashing,
        # or raising TypeError here if _json_value is unhashable).
        
        # For now, let's assume if _json_value is hashable, this works.
        # If _json_value is a list/dict, this line will raise a TypeError at runtime.
        try:
            # For complex JSON_ValueType, ww might need a more robust way to create a hash,
            # e.g., by converting mutable collections to immutable ones (list -> tuple).
            # However, standard JSON values (str, int, float, bool, None) are hashable.
            # Dictionaries and lists are not.
            if isinstance(self._json_value, (list, dict)):
                # Option 1: Make VNode unhashable if its value is unhashable
                raise TypeError(f"VNode with unhashable jvalue type {type(self._json_value)} cannot be hashed.")
                # Option 2: Try to create a hashable representation (e.g., tuple of sorted dict items)
                # This can be complex and might not always be what we want.
                # For simplicity, let's stick with Option 1 for now.
            return hash((self._jpath, self._json_value))
        except TypeError:
            # This handles the case where self._json_value is inherently unhashable (list/dict)
            # Re-raise with a more specific message or handle as per our design.
            # For VNodeList.count() and VNodeList.index() to work without VNode being hashable,
            # they rely on __eq__ only.
            # If you want VNode to be generally hashable for sets/dict keys,
            # you must ensure all its components are hashable.
            raise TypeError(f"VNode instances with unhashable jvalue (type: {type(self._json_value).__name__}) cannot be hashed.")





class VNodeList:
    """This class holds a list of VNodes: normalized JSON Paths and the JSON values to which they refer.
    It functions as a list-like container, supporting common sequence operations such as iteration
    (e.g., in a `for` loop), indexed access (`[]`), slicing, length checking (`len()`),
    membership testing (`in`), and reversal (`reversed()`). It also provides methods for
    modification like `append()`, `extend()`, and `clear()`.
    """
    _empty_instance: 'VNodeList | None' = None
    
    def __init__(self, node_list: list[VNode]) -> None:
        super().__init__()
        self._node_list: list[VNode] = node_list
        
    @classmethod
    def empty_instance(cls) -> 'VNodeList':
        """Return the empty VNodeList."""
        if VNodeList._empty_instance is None:
            VNodeList._empty_instance = VNodeList([])
        instance: "VNodeList" = VNodeList._empty_instance
        return instance
    
    @property
    def node_list(self) -> list[VNode]:
        """Return the list of VNodes managed by this VNodeList.
        
        Note: this class is itself a list-like container, so you can also use this VNodeList  instance itself
         in iteration contexts  without needing to call this method.
        """
        return self._node_list
    
    # @property
    # def value(self):
    #     """
    #     see section 2.4.2. Type Conversion, pg 36 RFC 9535
    #     Extraction of a value from a nodelist can be performed in several ways, so an implicit conversion
    #      from NodesType to ValueType may be surprising and has therefore not been defined.
    #     """
        
    def __repr__(self) -> str:
        repr_str = f"VNodeList(node_list={repr(self._node_list)})"
        return repr_str
        
    def is_empty(self) -> bool:
        """Return True if this container has zero elements. """
        return len(self._node_list) == 0
        
        
    def copy(self) -> 'VNodeList':
        """Return a shallow copy of this VNodeList instance. Element VNodes are intended to be non-mutable, although
         the underlying """
        return VNodeList(self._node_list.copy())

    def pretty_print(self, flag: str = '') -> None:
        """Display the VNodes of this instance in a more user-friendly format, one line per VNode.
        If flag =='-l', pretty prints the value with json.dumps(jvalue, indent==2)"""
        if len(self) == 0 :
            print("VNodeList is empty.")
            return
        
        header_line = f"VNodeList(len={len(self)} VNodes)"
        print(header_line)
        print('_'* len(header_line))
        
        for index, vnode in enumerate(self):
            line_num = f"{index:3}.    "
            line1 = f"{line_num}{vnode.jpath}"
            if flag == '-l':
                jvalue_str = json.dumps(vnode.jvalue, indent=2)
            else:
                jvalue_str = str(vnode.jvalue)
            line2 = f"{len(line_num) * ' '}{jvalue_str}"
            print(f"{line1}\n{line2}")
            
    def values(self) -> Iterator[JSON_ValueType]:
        """Return an iterator over the values of this VNodeList. """
        def value_generator() -> Generator[JSON_ValueType, None, None]:
            for vnode in self:
                yield vnode.jvalue
        return value_generator()
    
    
    def paths(self) -> Iterator[NormalizedJPath]:
        """Return an iterator over the NormalizedJpath paths of this VNodeList. """
        def paths_generator() -> Generator[NormalizedJPath, None, None]:
            for vnode in self:
                yield vnode.jpath
        return paths_generator()
        
        
    ############################
    # Container Methods
    ############################
    def __len__(self) -> int:
        return len(self._node_list) if self._node_list else 0
    
    def __getitem__(self, key: int | slice) -> 'VNode | VNodeList':
        """Return the VNode at the given index, or a slice of VNodes."""
        if isinstance(key, slice):
            # If you want slicing to return a new VNodeList instance:
            return VNodeList(self._node_list[key])
            # Otherwise, it will return a list[VNode] directly:
            #return self._node_list[key]
        return self._node_list[key]
    
    def __iter__(self) -> Iterator[VNode]:
        """Return an iterator over the VNodes in this VNodeList."""
        return iter(self._node_list)
    
    def __reversed__(self) -> Iterator[VNode]:
        return reversed(self._node_list)
    
    def __contains__(self, item: VNode) -> bool:
        return item in self._node_list
    
    # --- Other useful list-like methods ---
    def append(self, item: VNode) -> None:
        """Append a VNode to the end of the list."""
        if not isinstance(item, VNode):
            raise TypeError("Can only append VNode instances.")
        self._node_list.append(item)
    
    def extend(self, items: 'list[VNode] | VNodeList') -> None:
        """Extend the list by appending all items from the iterable."""
        if isinstance(items, VNodeList):
            self._node_list.extend(items._node_list)
        elif isinstance(items, list) and all(isinstance(i, VNode) for i in items):
            self._node_list.extend(items)
        else:
            raise TypeError("Can only extend with a list of VNodes or another VNodeList.")
    
    def clear(self) -> None:
        """Remove all items from the list."""
        self._node_list.clear()
    

# # Defined here instead of json_type_defs.py to prefent circular reference
# NodesType: TypeAlias = VNodeList

    
    
class NumberValue(EvaluatorValue):
    
    _value: int | float
    
    def __init__(self, value: int | float) -> None:
        super().__init__()
        self._value = value
    
    @override
    @property
    def value(self) -> int | float:
        return self._value
    
    def __repr__(self) -> str:
        value_str = f"{self._value}" if type(self._value) is int else f"{self._value:0.3f}"
        return f"NumberValue(value={value_str})"
        
    def __str__(self) -> str:
        value_str = f"{self._value}" if type(self._value) is int else f"{self._value:0.3f}"
        return f"{value_str}"

class StringValue(EvaluatorValue):
    _value: str
    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value)}")
        super().__init__()
        content_to_unescape = value[1:-1]  # remove quotes
        # todo a string literal won't always be a member name, e.g., 'red' in :  ?@.color == 'red'
        # we need to further research rules for converting string literals that aren't member names.
        member_name = unescape_string_content(content_to_unescape)
        self._value = member_name
        
    @override
    @property
    def value(self) -> str:
        return self._value
        
    def __repr__(self) -> str:
        return f"StringValue({self._value!r})"
    
    def __str__(self) -> str:
        return f"{self._value}"
    
class BooleanValue(EvaluatorValue):
    
    _value: bool
    def __init__(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError(f"value only be boolean values, got {type(value)}")
        super().__init__()
        self._value = value
    
    @staticmethod
    def value_for(bool_expr: bool) -> 'BooleanValue':
        if bool_expr:
            return BooleanValue(True)
        else:
            return BooleanValue(False)
        
    @override
    @property
    def value(self) -> bool:
        return self._value
    
    def __repr__(self) -> str:
        return f"BooleanValue(value={self._value})"
    
    def __str__(self) -> str:
        return f"{str(self._value).lower()}"
    
    def __bool__(self) -> bool:
        """Defines the truthiness of BooleanValue instances."""
        return self.value  # self.value is already True or False
    
    @override
    def __eq__(self, other: object) -> bool:
        """
        Compares this BooleanValue for equality with another object.

        - If 'other' is a BooleanValue, compares their underlying boolean states.
        - If 'other' is a Python bool, compares this BooleanValue's state to it.
        - For any other type, compares this BooleanValue's state to the
          truthiness of 'other' (i.e., bool(other)).
        
        Returns True if they are considered equal under these rules, False otherwise.
        Returns NotImplemented if the comparison cannot be performed (e.g., if bool(other) fails).
        """
        if isinstance(other, BooleanValue):
            return self._value == other._value
        
        if isinstance(other, bool): # Python's native bool
            return self._value == other
        
        # For any other type, compare our boolean value to the truthiness of 'other'.
        # This fulfills "compare itself to any type that supports the concept of 'truthiness'".
        try:
            # Compare our internal boolean state to the truthiness of the other object.
            # Python's bool() will use __bool__ if available, then __len__,
            # and finally default to True for most other objects.
            return self._value == bool(other)
        except Exception:
            # This case should be rare, as bool() is robust.
            # If bool(other) raises an unhandled exception,
            # it's standard practice to indicate the comparison isn't implemented.
            return NotImplemented

        
    def negate(self) -> 'BooleanValue':
        """Returns the logically opposite BooleanValue instance."""
        if self._value  == True:
            return BooleanValue(False).set_pos(self.position).set_context(self.context)
        else:  # self.value == False here
            return BooleanValue(True).set_pos(self.position).set_context(self.context)
    
    
class NullValue(EvaluatorValue):

    def __init__(self) -> None:
        super().__init__()
    
    @override
    @property
    def value(self) -> None:
        return None
    
    def __repr__(self) -> str:
        return f"NullValue(value={None})"
    
    def __str__(self) -> str:
        return "null"
    
    