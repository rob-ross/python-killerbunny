#  File: function.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#
import inspect
import re
import threading
from abc import abstractmethod
from enum import Enum
from typing import (TypeAlias, Union, Any, Self, cast, get_type_hints, get_origin, get_args)
from typing import override  # type: ignore

from killerbunny.evaluating.value_nodes import NullValue, VNode, StringValue
from killerbunny.evaluating.value_nodes import VNodeList
from killerbunny.parsing.node_type import ASTNodeType, ASTNode
from killerbunny.parsing.parser_nodes import RepetitionNode, RelativeQueryNode, JsonPathQueryNode, \
    RelativeSingularQueryNode, AbsoluteSingularQueryNode
from killerbunny.parsing.terminal_nodes import BooleanLiteralNode, NullLiteralNode, LiteralNode
from killerbunny.shared.json_type_defs import JSON_ValueType, JSON_VALUE_TYPES, JSON_ARRAY_TYPES, JSON_OBJECT_TYPES


################################################################################################
# FUNCTION TYPES -  see 2.4.1. Type System for Function Expressions, pg 35, RFC 9535
################################################################################################

# Nothing: pg 35 RFC 9535.
# The special result Nothing represents the absence of a JSON value and is distinct from any JSON value, including null.

class NothingType:
    """Singleton type for the Nothing instance. See page 35 RFC 9535.
     The special result Nothing represents the absence of a JSON value and is distinct
     from any JSON value, including null.
     """
    _instance: 'NothingType | None' = None
    _lock = threading.Lock()
    
    @classmethod
    def _init_instance(cls) -> 'NothingType':
        # Double-checked locking pattern:
        # First check (outside the lock) to avoid acquiring the lock if the instance already exists.
        # This is an optimization for performance in the common case where the instance is already created.
        if cls._instance is None:
            with cls._lock: # <--- 3. Acquire the lock
                # Second check (inside the lock) to ensure that another thread
                # didn't create the instance while the current thread was waiting for the lock.
                if cls._instance is None:
                    cls._instance = NothingType()
            # Lock is automatically released when exiting the 'with' block
        return cls._instance
    
    @classmethod
    def instance(cls) -> 'NothingType':
        """ Return a singleton instance of this class in a thread-safe manner.
        :return: The singleton instance of this class
        """
        if cls._instance is None:
            return cls._init_instance()
        return cls._instance
    
    def __repr__(self) -> str:
        return 'NothingType(Nothing)'
    
    def __str__(self) -> str:
        return 'Nothing'

Nothing = NothingType.instance()


class LogicalType(Enum):
    """A boolean enum class used to type function parameters and return types.
    
    See section 2.4.1. Type System for Function Expressions, pg 36 in RFC 9535
     "LogicalTrue and LogicalFalse are unrelated to the JSON values expressed by the literals true and false."
    
    These types exist solely for typing the value returned from a function_expr or typing arguments to a function_expr
    and are not to be used in any other context to represent boolean values. Use the BooleanValue class or Python's
    True and False primitives to represent boolean values.
    """
    LogicalTrue  = True
    LogicalFalse = False
    
    @staticmethod
    def value_for(bool_expr: bool) -> 'LogicalType':
        if bool_expr:
            return LogicalType.LogicalTrue
        else:
            return LogicalType.LogicalFalse
        
    def __bool__(self) -> bool:
        """Defines the truthiness of LogicalType instances."""
        return self.value  # self.value is already True or False
    
    def negate(self) -> 'LogicalType':
        """Returns the logically opposite LogicalType instance."""
        if self == LogicalType.LogicalTrue:
            return LogicalType.LogicalFalse
        else:  # self == LogicalType.LogicalFalse
            return LogicalType.LogicalTrue


# ValueType: per pg 35 RFC 9535, ValueType is any valid JSON type plus Nothing
ValueType: TypeAlias = Union['JSON_ValueType', NothingType]  # for type hints
VALUE_TYPES = (*JSON_VALUE_TYPES, NothingType)  # for isinstance()
NodesType: TypeAlias = VNodeList

class FunctionParamType(Enum):
    ValueType = ValueType
    LogicalType = LogicalType
    NodesType = NodesType
    
    def __str__(self) -> str:
        if self == FunctionParamType.ValueType:
            return 'ValueType'
        if self == FunctionParamType.LogicalType:
            return "LogicalType"
        
        return "NodesType"

class FunctionNode(ASTNode):
    """Base class for functions defined per section 2.4 Function Extensions, page 34, RFC 9535.
     
     This class encapsulates a function name, its return type, and the names and types of its parameters.
     It is distinct from a FunctionCallNode, which represents an invocation of a function, with actual argument
     values for each function parameter.
     """
    def __init__(self, func_name: str, func_type: 'FunctionParam', param_list: list['FunctionParam']) -> None:
        if not isinstance(param_list, list) :
            raise TypeError(f"Expected param_list to be list[FunctionParam], but got {type(param_list)}")
        super().__init__(ASTNodeType.FUNCTION)
        self._func_name:   str = func_name
        self._func_type:  'FunctionParam' = func_type
        self._param_list:  list['FunctionParam'] = param_list
        self.set_python_params()
    
    @property
    def func_name(self) -> str:
        return self._func_name
    
    @property
    def func_type(self) -> FunctionParamType:
        """Return the type of the function."""
        return self._func_type.param_type
    
    @property
    def return_param(self) -> 'FunctionParam':
        return self._func_type
    
    @property
    def param_list(self) -> list['FunctionParam']:
        return self._param_list

    @abstractmethod
    def eval(self, *args:list[Any], **kwargs:dict[str, Any]) -> Any:
        """Evaluate this function with the given arguments.
        
        Subclasses must implement this method with their specific parameter lists.
        When calling the eval method of a subclass, use keyword arguments to match
        the parameter names defined in that subclass.
        """
        pass
    
    def validate_args(self, args: "RepetitionNode") -> bool:
        """subclasses can override to do any special validation of arguments beyond type checking and ensuring the
        correct number of arguments"""
        return True
    
    def get_eval_type_hints(self):
        """Get the type hints of the eval method for this function node instance."""
        # Get the actual implementation of the eval method from the subclass
        eval_method = self.__class__.eval
        
        # Get the type annotations
        type_hints = get_type_hints(eval_method)
        
        # Extract parameter types (excluding 'self' and 'return')
        param_types = {
            name: hint for name, hint in type_hints.items()
            if name != 'return' and name != 'self'
        }
        
        # Get the return type
        return_type = type_hints.get('return', Any)
        
        return {
            'param_types': param_types,
            'return_type': return_type
        }
    
    def _types_compatible(self, annotation_type, expected_type):
        """Check if the annotation type is compatible with the expected type.
        
        This is a simplistic implementation - you might need to enhance it
        based on your specific type system.
        """
        # If expected_type is Any, any annotation_type is compatible
        if expected_type is Any:
            return True
        
        if annotation_type == expected_type:
            return True
        
        # Check for Union types
        origin = get_origin(annotation_type)
        if origin is Union:
            args = get_args(annotation_type)
            # If any of the union types match the expected type, it's compatible
            return any(self._types_compatible(arg, expected_type) for arg in args)
        
        # For simple types, direct comparison
        return annotation_type == expected_type

    def set_python_params(self) -> None:
        """Use the eval() signature to set the expected python arg types."""
        # Get the eval method of the subclass
        eval_method = self.__class__.eval
        
        # Get the signature of the method
        sig = inspect.signature(eval_method)
        parameters = list(sig.parameters.values())
        
        # Get expected parameter count from the function's parameter list
        expected_param_count = len(self._param_list)
        actual_param_count = len(parameters) - 1  # exclude `self`
        
        if actual_param_count != expected_param_count:
            raise ValueError(
                f"Eval method must have exactly {expected_param_count} parameters "
                f"(excluding 'self'), but found {actual_param_count}"
            )
        
        # Check if the parameter types match the declared FunctionParam types
        type_hints = self.get_eval_type_hints()
        param_types = type_hints['param_types']
        
        for i, (param_name, param_type) in enumerate(param_types.items()):
            # Get the expected type from the corresponding FunctionParam
            if i < len(self._param_list):
                function_param = self._param_list[i]
                function_param._python_type = param_type  # assign the python type based on the parameter hint
                
                # Check if the types are compatible?
        
        # Check return type compatibility
        return_type = type_hints['return_type']
        self._func_type._python_type = return_type
        expected_return_type = self._func_type.python_type
        if not self._types_compatible(return_type, expected_return_type):
            raise ValueError(
                f"Return type of eval method is '{return_type}', "
                f"but '{expected_return_type}' was declared in FunctionParam"
            )

class FunctionCallNode(ASTNode):
    """AST node for a function invocation. Encapsulates a FunctionNode and an argument value list.
    
    function_expr  ::=  function_name:IDENTIFIER "(" [ function_argument ( "," function_argument )* ] ")"

    """
    _function_node: FunctionNode
    _args:'RepetitionNode'
    
    def __init__(self, node: FunctionNode, args: 'RepetitionNode') -> None:
        if not isinstance(node, FunctionNode):
            raise TypeError(f"Expected FunctionNode, but got {type(node)}")
        if args.node_type != ASTNodeType.FUNC_ARG_LIST:
            raise TypeError(f"Expected arg_list.node_type to be ASTNodeType.FUNC_ARG_LIST, but got {args.node_type}")
        super().__init__(ASTNodeType.FUNCTION_CALL)
        
        self._function_node = node
        self._args:'RepetitionNode' = args
        self.set_pos(node._position.text, node._position.start, args._position.end)
        self._validate_args(args)
    
    @property
    def func_name(self) -> str:
        return self._function_node.func_name
    
    @property
    def func_node(self) -> FunctionNode:
        return self._function_node
    
    @property
    def func_args(self) -> 'RepetitionNode':
        return self._args
    
    @property
    def arg_types(self) -> list[ASTNodeType]:
        return []  #todo implement
    
    def __repr__(self) -> str:
        return f"FunctionCallNode(func_name={self._function_node.func_name}, func_args={self.func_args})"
    
    def __str__(self) -> str:
        arg_list = ', '.join( [ str(arg) for arg in self._args] )
        return f"{self._function_node.func_name}({arg_list})->{self._function_node.func_type}"
    
    def _validate_args(self, args: 'RepetitionNode') -> None:
        """Ensure that the number of args equals the number of defined parameters and that their types match. """
        param_list = self._function_node.param_list
        arg_count_diff = len(param_list) - len(args)
        if arg_count_diff != 0:
            if arg_count_diff < 0:
                pre_msg = "Too many"
            else:
                pre_msg = "Too few"
            msg = f"{pre_msg} arguments for {self._function_node.func_name}(). Expected {len(param_list)}, got {len(args)}"
            raise ValueError(msg)
        # special function validation
        self._function_node.validate_args(args)


class FunctionParam(ASTNode):
    
    def __init__(self, param_name: str, param_type: 'FunctionParamType', python_type: Any) -> None:
        """Represents a function parameter. This could either be a function return parameter or
        a function argument parameter.
        
        :param param_name: Formal name of the parameter. Although, all function args are passed by position, so this is
                            mainly to aid in debugging and logging
        :param param_type: The allowed type of the parameter.
        :param python_type: Can be used to narrow the parameter type to a specific Python type or types,
        e.g., int | Nothing, as in the return type of the length() function extension. 
          
        """
        if not isinstance(param_type, FunctionParamType):
            raise TypeError(f"Expected param_type to be FunctionParamType, but got {param_type}")
        
        super().__init__(ASTNodeType.FUNCTION_PARAM)
        self._param_name = param_name
        self._param_type = param_type
        self._python_type = python_type
    
    
    @property
    def param_name(self) -> str:
        return self._param_name
    
    @property
    def param_type(self) -> 'FunctionParamType':
        return self._param_type
    
    @property
    def python_type(self) -> Any:
        # todo this property may be redundant with param_type. We'll see how use cases for it develop
        return self._python_type
    

class FunctionArgument(ASTNode):
    """
    
    function_argument  ::=  logical_expr  |
                            filter_query  |  ; includes singular query
                            function_expr |
                            literal
    """
    _arg_node: ASTNode
    _arg_type: FunctionParamType
    _python_type: Any
    def __init__(self, node: ASTNode) -> None:
        super().__init__(ASTNodeType.FUNCTION_ARG)
        self._arg_node = node
        # these get set during validation
        self._arg_type = None  # type: ignore
        self._python_type = None # type: ignore
        
    @property
    def arg_node(self) -> ASTNode:
        return self._arg_node
    
    @property
    def arg_type(self) -> FunctionParamType:
        return self._arg_type
        
    @property
    def python_type(self) -> Any:
        return self._python_type
        
    def __repr__(self) -> str:
        return f"FunctionArgument(arg_node={self._arg_node!r})"
    
    def __str__(self) -> str:
        return f"{self._arg_node}"
        
    def _param_type_for_node(self, param: FunctionParam) -> tuple[FunctionParamType, Any] :
        """Determine the appropriate type for this argument, using the param for implicit conversions, if needed.
        E.g., a relative_query as an argument to a function with declared param NodesType will be typed as NodesType,
        VLNodesList. But the same relative_query argument to a parameter typed as LogicalType can be converted, so
        it will get typed as LogicalType."""
        arg_node = self._arg_node
        node_type = arg_node.node_type
        # literals
        if node_type == ASTNodeType.STRING:
            return FunctionParamType.ValueType, str
        elif node_type == ASTNodeType.INT:
            return FunctionParamType.ValueType, int
        elif node_type == ASTNodeType.FLOAT:
            return FunctionParamType.ValueType, float
        elif isinstance(arg_node, BooleanLiteralNode):
            return FunctionParamType.ValueType, bool
        elif isinstance(arg_node, NullLiteralNode):
            return FunctionParamType.ValueType, NullValue
        
        # logical_expr
        elif node_type == ASTNodeType.LOGICAL_EXPR or node_type == ASTNodeType.COMPARISON_EXPR:
            return FunctionParamType.LogicalType, LogicalType
        
        # function_expr
        elif isinstance(arg_node, FunctionCallNode):
            ret_type = arg_node.func_node.return_param
            if ret_type.param_type == FunctionParamType.NodesType and  param.param_type == FunctionParamType.LogicalType:
                return FunctionParamType.LogicalType, LogicalType  # this converts a NodeList type to LogicalType.
            return ret_type.param_type, ret_type.python_type
        
        # singluar query
        elif ( isinstance(arg_node, (RelativeSingularQueryNode, AbsoluteSingularQueryNode)) or
               ( arg_node.is_singular_query() and
               isinstance(arg_node, (RepetitionNode, JsonPathQueryNode, RelativeQueryNode )))
        ):
            if param.param_type == FunctionParamType.LogicalType:
                return FunctionParamType.LogicalType, LogicalType  # this converts a NodeList type to LogicalType.
            else:
                return FunctionParamType.ValueType, FunctionParamType.ValueType
        
        # filter_query
        elif isinstance(arg_node, (RelativeQueryNode, JsonPathQueryNode)):
            if param.param_type == FunctionParamType.LogicalType:
                return FunctionParamType.LogicalType, LogicalType  # this converts a NodeList type to LogicalType.
            else:
                return FunctionParamType.NodesType, VNodeList
        
        else:
            raise TypeError(f"Expected logical_expr, filter_query, function_expr, or literal but got {type(arg_node)}, node_type = {arg_node.node_type}")
    
    
    def validate_type(self, param: FunctionParam) -> bool:
        """Validate the type of the argument against the expected type of the param.
        
        See section 2.4.3. Well-Typedness of Function Expressions, page 36, RFC 9535"""
        self._arg_type,  self._python_type = self._param_type_for_node(param)
        if self._arg_type == param.param_type and self.python_type == param.python_type :
            return True  # exact type match, the simplest case
        
        """
        An argument is well-typed:
            when the argument is a function expression with the same declared result type as the declared type
            of the parameter.
        """
        if self.arg_node.node_type == ASTNodeType.FUNCTION_CALL:
            function_expr = cast(FunctionCallNode, self._arg_node )
            return_param = function_expr.func_node.return_param
            if return_param.param_type == self._arg_type:
                return True
            elif (return_param.param_type == FunctionParamType.NodesType and
                  self._arg_type == FunctionParamType.LogicalType):
                """A function expression of declared type NodesType can be used as a function argument for a parameter
                of declared type LogicalType, with the equivalent conversion rule:
                    • If the nodelist contains one or more nodes, the conversion result is LogicalTrue.
                    • If the nodelist is empty, the conversion result is LogicalFalse."""
                return True
            else:
                return False
        
        """
        An argument is well-typed:
            when the declared type of the parameter is NodesType and the argument is a query
            (which includes singular query).
        """
        if param.param_type == FunctionParamType.NodesType and self._arg_node.is_query():
            return True
        
        """
        An argument is well-typed:
            when the declared type of the parameter is ValueType and the argument is one of the following:
                ▪ A value expressed as a literal.
                ▪ A singular query. In this case:
                    ▪ If the query results in a nodelist consisting of a single node,
                        the argument is the value of the node.
                    ▪ If the query results in an empty nodelist, the argument is the special result Nothing.
        """
        if param.param_type == FunctionParamType.ValueType:
            if isinstance(self.arg_node, LiteralNode) or self._arg_node.is_singular_query():
                return True
            else:
                raise TypeError(f"Expected singular query for ValueType parameter")
                
        if self._arg_type != param.param_type:
            raise TypeError(f"Expected {param.param_type} but got {self._arg_type}")
        
        return True


####################################################################
# STANDARD FUNCTION EXTENSIONS
####################################################################


class LengthFunction(FunctionNode):
    """Compute the length of a str, Array, or Object value"""
    def __init__(self) -> None:
        return_param = FunctionParam("return", FunctionParamType.ValueType, (int, NothingType))
        # param1 = FunctionParam("value", FunctionParamType.ValueType, VALUE_TYPES )
        param1 = FunctionParam("value", FunctionParamType.ValueType, ValueType )
    
        super().__init__("length", return_param, [param1])
        
    
    def eval(self, value: ValueType) -> int | NothingType:  # type: ignore
        if isinstance(value, VNodeList):
            # there should only be one node in this nodelist.
            if len(value) == 1:
                val = value[0].jvalue
            elif value.is_empty():
                return Nothing
            else:
                raise ValueError(f"Single node VNNodeList arg expected, but got length of {len(value)}")
        else:
            val = value
        
        if isinstance(val, str):
            return len(val)
        if isinstance(val, JSON_ARRAY_TYPES):
            return len(val)
        if isinstance(val, JSON_OBJECT_TYPES):
            return len(val)
        
        return Nothing
    
class CountFunction(FunctionNode):
    """Obtain the number of nodes in a nodelist."""
    def __init__(self) -> None:
        return_param = FunctionParam("return", FunctionParamType.ValueType, int)
        param1 = FunctionParam("nodes", FunctionParamType.NodesType, VNodeList)
        super().__init__("count", return_param, [param1])

    def eval(self, nodes: NodesType) -> int:  # type: ignore
        """Return the number of nodes in the argument nodelist."""
        if nodes is None:
            raise ValueError(f"CountFunction.eval: nodes argument cannot be None.")
        if not isinstance(nodes, VNodeList):
            raise TypeError(f"`nodes` argument must be NodesType, but got {type(nodes)}")
        return len(nodes)
    
class RegexFuncBase(FunctionNode):
    """Base class of MatchFunction and SearchFunction, as they only differ in function name
    and regex method, either  `match` or `search`
    
    Its arguments are instances of ValueType (possibly taken from a singular query.
    If the first argument is not a string or the second argument is not a string conforming to [RFC9485],
    the result is LogicalFalse. Otherwise, the string that is the first argument is matched against the I-Regexp
    contained in the string that is the second argument; the result is LogicalTrue if the string matches the I-Regexp
    and is LogicalFalse otherwise.
    see 2.4.6. match() Function Extension, page 38, RFC 9535
    
    todo - at the moment we use Python's re implementation for regexps. This is a superset of I-regexp as described
    in the RFC 9535 spec.
    todo - implmenent an I-regexp validation regex to warn user if regex isn't compliant.
    
    """
    def __init__(self, function_name: str) -> None:
        return_param = FunctionParam("return", FunctionParamType.LogicalType, LogicalType)
        param1 = FunctionParam("string", FunctionParamType.ValueType, str)
        param2 = FunctionParam("iregexp_str", FunctionParamType.ValueType, str)
        super().__init__(function_name, return_param, [param1, param2])
    
    @abstractmethod
    def eval(self, string: str, iregexp_str: str) -> bool:  # type: ignore
        ...
    
    
    def _convert_args(self, string: str | StringValue | VNodeList, iregexp_str: str | StringValue | VNodeList) -> tuple[str, str]:
        """Convert argument values to str values. The search/match functions may be passed in a string literal or a
        single element VNodeList, from which we can obtain the value. """
        str_val: str
        if isinstance(string, VNodeList) and len(string) == 1 and isinstance(string[0].jvalue, (str, StringValue) ):   # type: ignore
            str_val = string[0].jvalue  # type: ignore
        elif isinstance(string, (str, StringValue) ):
            str_val = str(string)
        else:
            raise TypeError(f"First argument must be a str or single element VNodeList assignable to str, got {type(string).__name__}")
        
        if isinstance(iregexp_str, VNodeList) and len(iregexp_str) == 1 and isinstance(iregexp_str[0].jvalue, str):  # type: ignore
            regex_str = str(iregexp_str[0].jvalue)  # type: ignore
        elif isinstance(iregexp_str, (str, StringValue) ):
            regex_str = str(iregexp_str)
        else:
            raise TypeError(f"Second argument must be a str, or single element VNodeList assignable to str, got {type(iregexp_str).__name__}")
            
        return str_val, regex_str
    
    @override
    def validate_args(self, args: "RepetitionNode") -> bool:
        """Verify that the regexp str will compile and warn if it doesn't comply with I-regexp spec.
        :raise: re.error if the regexp is not supported by the re library
        """
        if args is None:
            raise ValueError(f"MatchFunction.validate_args: args argument cannot be None.")
        if not isinstance(args, RepetitionNode):
            raise TypeError(f"Expected args to be RepetitionNode, received {type(args)}")
        if args.node_type != ASTNodeType.FUNC_ARG_LIST:
            raise TypeError(f"Expected args to be FUNC_ARG_LIST, received {args.node_type}")
        if len(args) != len(self._param_list):
            raise ValueError(f"Expected {len(self._param_list)} arguments, but got {len(args)}")
        
        re_str = str(args[1])
        re.compile(re_str)  # will raise re.error if `re` doesn't support the regexp
        
        return True

class MatchFunction(RegexFuncBase):
    """Check whether (the entirety of; see Section 2.4.7) a given string matches a given regular expression."""
    def __init__(self) -> None:
        super().__init__("match")
    
    @override
    def eval(self, string: str, iregexp_str: str) -> LogicalType:  # type: ignore
        try:
            str_val, regex_str = self._convert_args(string, iregexp_str)
        except TypeError:
            return LogicalType.value_for(False)
        return LogicalType.value_for( re.fullmatch( regex_str, str_val) is not None )

class SearchFunction(RegexFuncBase):
    """Check whether a given string contains a substring that matches a given regular expression,"""
    def __init__(self) -> None:
        super().__init__("search")
    
    @override
    def eval(self, string: str, iregexp_str: str) -> LogicalType:  # type: ignore
        try:
            str_val, regex_str = self._convert_args(string, iregexp_str)
        except TypeError:
            return LogicalType.value_for(False)
        return LogicalType.value_for( re.search( regex_str, str_val) is not None )


class ValueFunction(FunctionNode):
    """Convert an instance of NodesType to a value.
        • If the argument contains a single node, the result is the value of the node.
        • If the argument is the empty nodelist or contains multiple nodes, the result is Nothing.
    """
    def __init__(self) -> None:
        return_param = FunctionParam("return", FunctionParamType.ValueType, VALUE_TYPES)
        param1 = FunctionParam("node", FunctionParamType.NodesType, (NodesType,))
        super().__init__("value", return_param, [param1])
        
    def eval(self, node: NodesType) -> ValueType:  # type: ignore
        return_value: ValueType = Nothing
        if isinstance(node, VNodeList) :
            if len(node) == 1:
                return_value =  node[0].jvalue  # type: ignore
        elif isinstance(node, VNode):
            return_value =  node.jvalue

        return return_value



class _FunctionRegistry:
    """Singleton manager of registered Function extensions. """
    functions: dict[str, FunctionNode]
    
    _instance: '_FunctionRegistry | None' = None
    _lock = threading.Lock()
    
    def __init__(self) -> None:
        self.functions = {}
        
    @classmethod
    def _init_instance(cls) -> '_FunctionRegistry':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = _FunctionRegistry()
        return cls._instance
    
    @classmethod
    def instance(cls) -> '_FunctionRegistry':
        """ Return a singleton instance of this class in a thread-safe manner.
        :return: The singleton instance of this class
        """
        if cls._instance is not None:
            return cls._instance
        else:
            return cls._init_instance()
    
    @classmethod
    def register_known_functions(cls) -> None:
        known_functions: list[FunctionNode] = [
            LengthFunction(), CountFunction(), MatchFunction(), SearchFunction(), ValueFunction()
        ]
        for func in known_functions:
            cls.instance().register(func)
        
    def register(self, func: FunctionNode) -> Self:
        self.functions[func.func_name] = func
        return self
    
    def lookup(self, func_name: str) -> FunctionNode | None:
        return self.functions.get(func_name, None)

_FunctionRegistry.register_known_functions()

def get_registered_function(func_name: str) -> FunctionNode | None:
    return _FunctionRegistry.instance().lookup(func_name)


def register_function(func: FunctionNode):
    """Register an instance of a FunctionNode. """
    _FunctionRegistry.instance().register(func)
