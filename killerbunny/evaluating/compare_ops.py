#  File: compare_ops.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

"""
ComparisonOperatorType:
    Types for comparison operators, and implementations of comparison operations between JSON value types
    and evaluator EvaluatorValue object types.
    
Implements comparison evaluation rules as specified in section 2.3.5.2.2. Comparisons, pg 28, RFC 9535

"""
import logging
from enum import Enum
from typing import cast

from killerbunny.evaluating.value_nodes import NumberValue, VNode, \
    BooleanValue
from killerbunny.evaluating.evaluator_types import EvaluatorValue, NormalizedJPath
from killerbunny.shared.json_type_defs import JSON_ObjectType, JSON_ARRAY_TYPES, \
    JSON_OBJECT_TYPES, JSON_ArrayType, JSON_STRUCTURED_TYPES, JSON_VALUE_TYPES
from killerbunny.parsing.function import NothingType, ValueType
from killerbunny.lexing.tokens import TokenType

_logger = logging.getLogger(__name__)

# Helper function to unwrap ValueNode instances to their raw JSON_ValueType
def _unwrap(operand: EvaluatorValue | ValueType) -> ValueType:
    """
    Unwraps a EvaluatorValue (from value_nodes.py) to its underlying raw JSON_ValueType.
    If the operand is already a raw JSON_ValueType, it is returned directly.
    """
    if isinstance(operand, NumberValue):
        return operand.value
    # Add elif isinstance(operand, StringValue): return operand.value
    # Add elif isinstance(operand, BooleanValue): return operand.value
    # Add elif isinstance(operand, ArrayValue): return operand.value # if ArrayValue wraps a list
    # Add elif isinstance(operand, ObjectValue): return operand.value # if ObjectValue wraps a dict
    # Add elif isinstance(operand, NullValue): return operand.value # if NullValue wraps None

    elif isinstance(operand, EvaluatorValue):
        return operand.value
    elif isinstance(operand, JSON_VALUE_TYPES):
        # If it's not an instance of EvaluatorValue (or any of its subclasses),
        # it's assumed to be a raw ValueType already.
        return operand
    elif isinstance(operand, NothingType):
        return operand
    else:
        raise NotImplementedError(
            f"Unwrapping for operand type {type(operand).__name__} is not implemented. "
            "Ensure it has a '.value' property or is handled in _unwrap."
        )


class ComparisonOperatorType(Enum):
    EQ = TokenType.EQUAL
    NE = TokenType.NOT_EQUAL
    GTE = TokenType.GTE
    LTE = TokenType.LTE
    GT = TokenType.GT
    LT = TokenType.LT
    
    
    @staticmethod
    def _depth_exceeded(depth: int, max_depth: int, left_path: str, right_path: str ) -> bool:
        """Return True and log warning if depth exceeds max_depth, otherwise return False and log nothing."""
        if depth >= max_depth:
            _logger.warning(f"Max traversal depth ({max_depth}) reached at path left: {left_path}, right: {right_path}")
            return True
        return False
    
    @staticmethod
    def _cycle_detected(left_node: VNode,
                        left_ids: dict[int, VNode] ,
                        right_node: VNode,
                        right_ids: dict[int, VNode],
                        ) -> bool:
        """Return True and log a warning if a circular reference cycle is detected.
        Detect a cycle by comparing node value ids to previously seen object ids. If a cycle is detected, return True
        and log a warning. Otherwise, store the ids of non-scalar (array or object) jvalues
        in the left_node and right_node to the left_id and right_id dicts. Scalar types don't cause cycles, only
        vectors (list/dict) can.
        """
        
        """
         # todo more testing required. Do we have to worry about the left referencing the same object in the right,
        # that references an ancestor object in the left? Our checks also have to be smart about overall identity
        # as well ; if left and right are the *same* object they should return true for equal. But our
        # cross list checks might flag this case as a cycle.
        """
        
        l_val = left_node.jvalue
        r_val = right_node.jvalue
        
        # only lists and dicts can create cyclic dependancies, we ignore scalars
        if isinstance(l_val, JSON_STRUCTURED_TYPES):
            if id(l_val) in left_ids:
                _logger.warning(
                    f"Circular reference cycle detected: left value: {left_node} already included as:"
                    f" {left_ids[id(l_val)]}"
                )
                return True
            else:
                left_ids[id(l_val)] = left_node
        
        if isinstance(r_val, JSON_STRUCTURED_TYPES):
            if id(r_val) in right_ids:
                _logger.warning(
                    f"Circular reference cycle detected: right value: {right_node} already included as:"
                    f" {right_ids[id(r_val)]}"
                )
                return True
            else:
                right_ids[id(r_val)] = right_node
        # no cycles detected
        return False

    @staticmethod
    def _eval_eq(left_raw: ValueType,
                 right_raw: ValueType,
                 left_ids:  dict[int, VNode]  | None = None,
                 right_ids: dict[int, VNode]  | None = None,
                 left_path:  str = '',
                 right_path: str = '',
                 cur_depth: int = 0,
                 max_depth: int = 32,
                 ) -> bool:
        """
        Implements the '==' comparison based on RFC 9535 comparison rules
        
        Assumes operands are already unwrapped raw JSON_VALUEs (and including Nothing).
        see  2.3.5.2.2. Comparisons, pg 28, RFC 9535
        
        Returns False if max_depth recursive calls are reached, or if a cyclic dependency is detected.
        
        Top-level caller of this method should only pass in left_raw and right_raw. The other arguments are populated
        during recursion. I.e.,
            ...
            if ( ComparisonOperatorType._eval_eq( "apple", "apple") :
                ...
        """
        # Handle Nothing (empty nodelist)
        if isinstance(left_raw, NothingType) and isinstance(right_raw, NothingType):
            return True
        if isinstance(left_raw, NothingType) or isinstance(right_raw, NothingType):
            return False
        
        # Handle numbers (I-JSON considerations are simplified to Python's direct comparison)
        if isinstance(left_raw, (int, float)) and isinstance(right_raw, (int, float)):
            return left_raw == right_raw
        
        # Handle other primitive values (null, boolean, string)
        # If types are different at this point (and not both numbers), they are not equal.
        if type(left_raw) != type(right_raw):
            return False
        
        # Now types are the same (and not Nothing, and not both numbers)
        if left_raw is None: # and right_raw is also None due to type check
            return True
        if isinstance(left_raw, bool): # and right_raw is also bool
            return left_raw == right_raw
        if isinstance(left_raw, str): # and right_raw is also str
            return left_raw == right_raw
        
        # We only have to worry about circular references for vector types, i.e. arrays and objects (lists and dicts).
        # The id lookup dicts left_ids and right_ids are initialized in the top level invocation
        # of the recursive descent of this method and then passed on the stack in subsequent recursive calls
        if left_ids is None:
            # first element treated as root
            left_raw_value = {} if isinstance(left_raw, NothingType) else left_raw
            left_root = VNode(NormalizedJPath("$"), left_raw_value, left_raw_value, 0)
            left_ids = { id(left_root) : left_root }
            left_path = "$"
        if right_ids is None:
            # first element treated as root
            right_raw_value = {} if isinstance(right_raw, NothingType) else right_raw
            right_root = VNode(NormalizedJPath("$"), right_raw_value, right_raw_value, 0)
            right_ids = { id(right_root) : right_root }
            right_path = "$"
        
        # Handle arrays
        if isinstance(left_raw, JSON_ARRAY_TYPES): # implies right_raw is also an array
            if not isinstance(right_raw, JSON_ARRAY_TYPES): return False # Should be caught by type(left)!=type(right)
            
            left_list = cast(JSON_ArrayType, left_raw)
            right_list = cast(JSON_ArrayType, right_raw)
            if len(left_list) != len(right_list):
                return False
            
            # Safeguard check:
            if ComparisonOperatorType._depth_exceeded(cur_depth, max_depth, left_path, right_path):
                return False
            
            for i in range(len(left_list)):
                # Recursively call _eval_eq for elements
                one_deeper = cur_depth + 1
                left_node  = VNode(NormalizedJPath( f"{left_path}[{i}]"),  left_list[i],   None,  one_deeper)
                right_node = VNode(NormalizedJPath( f"{right_path}[{i}]"), right_list[i],  None, one_deeper)
                left_path = left_node.jpath.jpath_str
                right_path = right_node.jpath.jpath_str
                if ComparisonOperatorType._cycle_detected(left_node, left_ids, right_node, right_ids):
                    return False

                
                if not ComparisonOperatorType._eval_eq(
                        left_node.jvalue, right_node.jvalue, left_ids, right_ids,
                        left_path, right_path, one_deeper):
                    return False
                
            return True
        
        # Handle objects
        if isinstance(left_raw, JSON_OBJECT_TYPES): # implies right_raw is also an object
            if not isinstance(right_raw, JSON_OBJECT_TYPES): return False # Should be caught by type(left)!=type(right)
            
            left_obj = cast(JSON_ObjectType, left_raw)
            right_obj = cast(JSON_ObjectType, right_raw)
            
            if len(left_obj) != len(right_obj): # Different number of keys
                return False
            if set(left_obj.keys()) != set(right_obj.keys()): # Different key sets
                return False
            
            # Safeguard check:
            if ComparisonOperatorType._depth_exceeded(cur_depth, max_depth, left_path, right_path):
                return False
            
            for key in left_obj:
                # Recursively call _eval_eq for values
                one_deeper = cur_depth + 1
                left_node  = VNode(NormalizedJPath( f"{left_path}['{key}']"),  left_obj[key], None, one_deeper)
                right_node = VNode(NormalizedJPath(f"{right_path}['{key}']"), right_obj[key], None, one_deeper)
                left_path = left_node.jpath.jpath_str
                right_path = right_node.jpath.jpath_str
                
                if not ComparisonOperatorType._eval_eq(
                        left_node.jvalue, right_node.jvalue, left_ids, right_ids,
                        left_path, right_path, one_deeper ):
                    return False
                
            return True
        
        # Fallback for any unhandled same-type comparison (should ideally not be reached
        # if all JSON types are covered above)
        return False


    @staticmethod
    def _eval_lt(left_raw: ValueType, right_raw: ValueType) -> bool:
        """
        Implements the '<' comparison based on RFC 9535, 2.3.5.2.2.
        Assumes operands are already unwrapped raw JSON_VALUEs (including Nothing).
        """
        # Handle Nothing (empty nodelist) - comparison with < always yields false
        if isinstance(left_raw, NothingType) or isinstance(right_raw, NothingType):
            return False
        
        # Comparison only defined for numbers or strings
        if isinstance(left_raw, (int, float)) and isinstance(right_raw, (int, float)):
            return left_raw < right_raw
        
        if isinstance(left_raw, str) and isinstance(right_raw, str):
            # Python's string comparison aligns with Unicode scalar value comparison
            return left_raw < right_raw
        
        # All other cases (different types, or types not number/string like null, bool, array, object)
        return False
    
    
    def eval(
            self,
            left_operand:  EvaluatorValue | ValueType,
            right_operand: EvaluatorValue | ValueType
        ) -> BooleanValue:
        """
        Evaluate the comparison operation between left and right operands and return
        a BooleanValue value
        Operands can be
            EvaluatorValue wrappers like Number, String, BooleanValue, etc.,
            raw JSON_VALUEs like Python ints, floats, strs, etc.,
            or the special value Nothing).
        The evaluator is responsible for resolving nodelists from path expressions
        to a single value or Nothing before calling this method.
        Returns BooleanValue
        """
        
        # we compare JSON value types (i.e., native Python types like str, int, float, list, dict, etc.)
        # but we can accept wrapper EvaluatorValue objects as well. In these cases, the Python values need to be extracted from
        # the wrapper objects first.
        left_raw  = _unwrap(left_operand)
        right_raw = _unwrap(right_operand)
        
        # Assignment to False is for the linter. The match statement is exhaustive and always gets set to a value
        result_bool: bool = False
        match self:
            case ComparisonOperatorType.EQ:
                result_bool = ComparisonOperatorType._eval_eq(left_raw, right_raw)
            case ComparisonOperatorType.NE:
                # a != b yields true if and only if a == b yields false.
                result_bool = not ComparisonOperatorType._eval_eq(left_raw, right_raw)
            case ComparisonOperatorType.LT:
                result_bool = ComparisonOperatorType._eval_lt(left_raw, right_raw)
            case ComparisonOperatorType.LTE:
                # a <= b yields true if and only if a < b yields true or a == b yields true.
                if ComparisonOperatorType._eval_lt(left_raw, right_raw):
                    result_bool = True
                else:
                    result_bool = ComparisonOperatorType._eval_eq(left_raw, right_raw)
            case ComparisonOperatorType.GT:
                # a > b yields true if and only if b < a yields true.
                result_bool = ComparisonOperatorType._eval_lt(right_raw, left_raw) # Note swapped operands
            case ComparisonOperatorType.GTE:
                # a >= b yields true if and only if b < a yields true or a == b yields true.
                if ComparisonOperatorType._eval_lt(right_raw, left_raw): # Note swapped operands for b < a
                    result_bool = True
                else:
                    result_bool = ComparisonOperatorType._eval_eq(left_raw, right_raw)
        
        return BooleanValue.value_for(result_bool)  # calling method responsible for setting pos and context on this

# COMPARISON_OP_TYPE_LOOKUP: given a comparison operator TokenType, we can lookup the ComparisonOperatorType
COMPARISON_OP_TYPE_LOOKUP: dict[TokenType, ComparisonOperatorType] = {
    item.value: item for item in ComparisonOperatorType
}