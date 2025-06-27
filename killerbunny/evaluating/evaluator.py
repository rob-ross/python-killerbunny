#  File: evaluator.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#


"""Evaluates a jsonpath query"""
import logging
from collections import deque
from typing import Callable, NamedTuple, TypeAlias, Union, cast, Any

from killerbunny.evaluating.compare_ops import COMPARISON_OP_TYPE_LOOKUP
from killerbunny.evaluating.evaluator_types import EvaluatorValue, NormalizedJPath
from killerbunny.evaluating.runtime_result import RuntimeResult
from killerbunny.evaluating.value_nodes import (
    VNodeList,
    VNode,
    NumberValue,
    BooleanValue,
    NullValue,
    StringValue
)
from killerbunny.parsing.function import Nothing, LogicalType, ValueType, FunctionCallNode, FunctionArgument
from killerbunny.parsing.node_type import ASTNode, ASTNodeType
from killerbunny.parsing.parser_nodes import (
    JsonPathQueryNode,
    SegmentNode,
    RelativeQueryNode,
    RepetitionNode,
    UnaryOpNode,
    BinaryOpNode,
    RelativeSingularQueryNode,
    AbsoluteSingularQueryNode
)
from killerbunny.parsing.selector_nodes import (
    NameSelectorNode,
    WildcardSelectorNode,
    SliceSelectorNode,
    IndexSelectorNode,
    FilterSelectorNode
)
from killerbunny.parsing.terminal_nodes import (
    RootNode,
    NumericLiteralNode,
    BooleanLiteralNode,
    NullLiteralNode,
    StringLiteralNode,
    IdentifierNode
)
from killerbunny.shared.constants import (
    ROOT_JSON_VALUE_KEY,
    SEGMENT_INPUT_NODELIST_KEY,
    FILTER_SELECTOR_INPUT_NODE_KEY,
    CURRENT_NODE_KEY,
    JPATH_QUERY_RESULT_NODE_KEY
)
from killerbunny.shared.context import Context
from killerbunny.shared.errors import RTError, Error
from killerbunny.shared.json_type_defs import (
    JSON_PRIMITIVE_TYPES,
    JSON_ARRAY_TYPES,
    JSON_OBJECT_TYPES,
    JSON_STRUCTURED_TYPES,
    JSON_VALUE_TYPES
)
from killerbunny.shared.position import Position

_logger = logging.getLogger(__name__)


ComparableType: TypeAlias = Union[ValueType, EvaluatorValue]

####################################################################
# EVALUATOR
####################################################################
# noinspection PyPep8Naming,PyMethodMayBeStatic,DuplicatedCode
class JPathEvaluator:
    """Evaluates a json path query string, in the form of an AST, for the json path query argument stored in the supplied
    Context. The main entry point is visit(), which is passed an AST from a successful parse result, along with
    a Context in which a json value has been set for the key ROOT_JSON_VALUE_KEY. This is the value of the root node
    against which the query is evaluated.
    The visit() method may be called with any ASTNode produced by the JPathParser.subparse() method. This allows testing
    of any grammar production, such as comparison_expression, for example. If the ASTNode tree references the current node
    i.e., contains a CurrentNodeIdentifier node, it is expected that a json value with the key CURRENT_NODE_KEY has been
    set in the Context, otherwise the evaluation will fail.
    Per RFC 9535, the evaulation phase of the json path query cannot fail and no errors are reported to the caller.
    Instead, references to non-existant member values or elements are silently ignored. However, this method will log
    warning messages to this module's logger in these situtations.
    
    todo - add config options to control error reporting,
    perhaps as a choice of silent, returning an Error instance, logging at user-defined levels, and raising exceptions.
    In a production environment, raising exceptions might not be the best design choice, however, it may be valuable
    during development to fail-fast.
    """
    
    def visit(self, node: ASTNode, context: Context) -> RuntimeResult:
        method_name = f"visit_{type(node).__name__}"
        method: Callable[[ASTNode, Context], RuntimeResult] = getattr(self, method_name, self.no_visit_method)
        return method( node, context)
    
    def no_visit_method(self, node: ASTNode, context: Context) -> RuntimeResult:
        raise NotImplementedError(f"No visit_{type(node).__name__} method defined")
    
    ####################################################################

    def visit_RootNode(self, node: RootNode, context: Context) -> RuntimeResult:
        """Set the JSON path query argument in the RootNode.
        This value is used by the JSON path query to generate ouput nodes that
        match the query parameters. The value is obtained from the Context's symbol table with the key
        given by ROOT_JSON_VALUE_KEY.
        :return: The root nodelist in RuntimeResult.value
        """
        rt_res = RuntimeResult()
        root_json_value = context.get_symbol(ROOT_JSON_VALUE_KEY)
        if root_json_value is None:
            # todo this case represents a programming error. Perhaps in this case the proper solution
            #  is to raise an Exception
            return rt_res.failure(RTError(node.position,
                            f"No JSON value set for {ROOT_JSON_VALUE_KEY} in current Context.", context))
        node.json_value = root_json_value
        return rt_res.success(node.root_nodelist)

    def visit_JsonPathQueryNode(self, node: JsonPathQueryNode, context: Context) -> RuntimeResult:
        """This node can represent the main entry point in the query, i.e., the entire JSON path query string
        starting with $, or it can represent an AbsoluteSingularQueryNode used inside a filter-selector.
        Write the result of the query to the context with JPATH_QUERY_RESULT_NODE_KEY.
        If this is the top-level JsonPathQueryNode, this is the final nodelist output of the query.
        
        returns: VNodeList in RunttimeResult.value
        """
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = rt_res.register(self.visit_RootNode(node.root_node, context))
        if rt_res.error: return rt_res
        segment_output: VNodeList = input_nodelist  # default, in case there are no segments
        
        segments: RepetitionNode = node.segments
        if segments.is_empty():
            # no segments in the absolute query, so allow all input nodes
            context.set_symbol(JPATH_QUERY_RESULT_NODE_KEY, input_nodelist)
            return rt_res.success(BooleanValue.value_for(True).set_context(context).set_pos(node.position.copy()))
            
        
        for seg_node in segments:
            # creating a new Context provides a local scope for the segment visit
            seg_context = Context("<segment>", context, seg_node.position )
            seg_context.set_symbol(SEGMENT_INPUT_NODELIST_KEY, input_nodelist)
            segment_output = rt_res.register(self.visit(seg_node, seg_context))
            if rt_res.error: return rt_res
            input_nodelist = segment_output   # output of this segment becomes input for the next segment
        
        # the last segment output is the final output nodelist
        context.set_symbol(JPATH_QUERY_RESULT_NODE_KEY, segment_output)
        return rt_res.success(segment_output)
 
    
    def _collect_vnodes_and_their_descendants(self,
                                              initial_vnode: VNode,
                                              max_depth: int = 32,
                                              ) -> VNodeList:
        """
        Performs a breadth-first collection of VNodes, starting with the initial VNode,
        then its children, then grandchildren, etc.
        Each collected item is a VNode with its correct path.
        Handles circular references/cycle detection using VNode.jvalue's id(). If an object node has already been seen,
        it will not be added to the output VNodeList, and the cyclic nodes are logged with a warning
        Prevents descending further than max_depth levels deep. Paths deeper than this are not included
        in the output VNodeList and are logged with a warning.
        """
        collected_vnodes: list[VNode] = []
        instance_ids: dict[int, VNode] = {}  # keeps track of instance ids to detect circular references

         # Queue for BFS: (VNode, current_depth)
        node_queue = deque([(initial_vnode, 0)])
        
        while node_queue:
            cur_node, depth = node_queue.popleft()
            jpath = cur_node.jpath
            jvalue = cur_node.jvalue
            if isinstance(jvalue, JSON_PRIMITIVE_TYPES):
                continue  # primitives don't have children
            if depth >= max_depth:
                _logger.warning(f"Max traversal depth ({max_depth}) reached at path ({jpath})")
                continue
            if isinstance(jvalue, JSON_STRUCTURED_TYPES) and not isinstance(jvalue, str):
                # only structured types can have children, which can cause cycles. str included just in case, because
                # JSON_STRUCTURED_TYPES allows Sequence, and str is a Sequence
                if id(jvalue) in instance_ids:
                    _logger.warning(f"Circular reference cycle detected: current node: {cur_node} already included as: {instance_ids[id(jvalue)]}")
                    continue  # prevent circular reference cycles
                instance_ids[id(jvalue)] = cur_node
            collected_vnodes.append(cur_node)
            
            # add children to the queue for processing during the next iteration
            if isinstance(jvalue, JSON_ARRAY_TYPES):
                for index, element in enumerate(jvalue):
                    new_node = VNode(NormalizedJPath(f"{jpath}[{index}]"), element,
                                     cur_node.root_value, cur_node.node_depth + 1 )
                    node_queue.append((new_node, depth + 1))
            elif isinstance(jvalue, JSON_OBJECT_TYPES):
                for name, value in jvalue.items():
                    new_node = VNode(NormalizedJPath(f"{jpath}['{name}']"), value,
                                     cur_node.root_value, cur_node.node_depth + 1)
                    node_queue.append((new_node, depth + 1))
                    
        return VNodeList(collected_vnodes)
        
    def _children_of(self, parent_node: VNode) -> VNodeList:
        """Return the children of the argument node.
        
        See section 1.1., "Terminology", pg 6, RFC 9535
        Children (of a node): If the node is an array, the nodes of its elements; if the node is an object,
        the nodes of its member values. If the node is neither an array nor an object, it has no children.
        
        This method will detect a cycle when a child of the parent node `parent_node` is the same instance as the
        parent node, as determined by calling id() on the parent and child nodes. In this case, that child will not
        be included in the retrned VNodeList.
        """
        child_nodes: list[VNode] = []
        instance_ids: dict[int, VNode] = {id(parent_node.jvalue):parent_node}
    
        if isinstance(parent_node.jvalue, JSON_STRUCTURED_TYPES):
            base_path = parent_node.jpath
            if isinstance(parent_node.jvalue, JSON_ARRAY_TYPES):
                for index, element in enumerate(parent_node.jvalue):
                    element_path = NormalizedJPath(f"{base_path}[{index}]")
                    vnode = VNode(element_path, element, parent_node.root_value, parent_node.node_depth + 1)
                    if id(element) in instance_ids:
                        _logger.warning(f"Circular reference cycle detected: child node: {vnode} same as parent: {instance_ids[id(element)]}")
                        #print(f"\n+++Circular reference cycle detected: current node: {vnode} already included as: {instance_ids[id(element)]}")
                        continue
                    child_nodes.append(vnode)
            elif isinstance(parent_node.jvalue, JSON_OBJECT_TYPES):
                for member_name, member_value in parent_node.jvalue.items():
                    element_path = NormalizedJPath(f"{base_path}['{member_name}']")
                    vnode = VNode(element_path, member_value, parent_node.root_value, parent_node.node_depth + 1)
                    if id(member_value) in instance_ids:
                        _logger.warning(f"Circular reference cycle detected: child node: {vnode} same as parent: {instance_ids[id(member_value)]}")
                        #print(f"\n+++Circular reference cycle detected: current node: {vnode} already included as: {instance_ids[id(member_value)]}")
                        continue
                    child_nodes.append(vnode)
        
        return VNodeList(child_nodes)
        
    
    def visit_DescendantSegment(self, node: SegmentNode, context: Context) -> RuntimeResult:
        """Descendant segment creates and input nodelist from all input nodes and all descendants of input nodes.
        Drill down into all children of all nodes in the input VNodeList and apply all selectors
        to produce a concatenated output VNodeList
        2.5.2.2. Semantics, pg 43 RFC 9535
        A descendant segment produces zero or more descendants of an input value.
        For each node in the input nodelist, a descendant selector visits the input node and each of its descendants
        such that:
            • nodes of any array are visited in array order, and
            • nodes are visited before their descendants. (breadth-first - ed.)
        """
        
        """
        todo - further analyze this algorithm. The triple nested loop doesn't worry me *too* much at the moment because
        every input node and its descendants are visited once by each selector. However, it seems odd to me that
        selectors are called while descendants are still being collected. It seems like we could construct an input
        nodelist with all the nodes that need to be visited, then apply each selector to the same input nodelist.
        However, this algorithm follows the RFC's description so it may be that changing this algorithm produces
        output nodes in a different order than the spec requires.
        Collecting all input nodes first might make it easier to process segments in general. But at the moment,
        this works with my ad-hoc tests I have tried, so I will circle back to this later. Especially when I write
        detailed unit tests for this method
        """
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = context.get_symbol(SEGMENT_INPUT_NODELIST_KEY)
    
        # This list will hold the final aggregated results for the entire segment
        overall_segment_results: list[VNode] = []
        
        # Outer loop: "For each node in the input nodelist"
        # Let's call the current node from the input nodelist 'current_d1_vnode'
        # as it represents D1 for this particular iteration.
        for current_d1_vnode in input_nodelist:
            
            # This list will accumulate R1 + R2 + ... + Rn for the current_d1_vnode
            r_values_for_current_d1: list[VNode] = []
            
            # Step 1: Collect D1...Dn for the current_d1_vnode.
            # Di_vnode_sequence will be [D1_vnode, D2_vnode, ..., Dn_vnode]
            # where D1_vnode is current_d1_vnode.
            di_vnode_sequence: VNodeList = self._collect_vnodes_and_their_descendants(current_d1_vnode)
            
            instance_ids: dict[int, VNode] = {}  # keeps track of instance ids to detect circular references
        
            # Inner loop: "For each i such that 1 <= i <= n" (iterating through D1...Dn)
            # Let's call the current node from this sequence 'di_from_sequence'.
            di_from_sequence: VNode
            for di_from_sequence in di_vnode_sequence:
                instance_ids[id(di_from_sequence.jvalue)] = di_from_sequence
                
                # Ri is the result of applying the child segment [<selectors>] to di_from_sequence
                
                # Create a temporary VNodeList containing only di_from_sequence,
                # as selectors expect a VNodeList as input.
                temp_input_for_selectors = VNodeList([di_from_sequence])
                
                # This list will hold the results of applying *all* selectors to the *current* di_from_sequence.
                # This is effectively Ri for the current di_from_sequence.
                ri_for_this_di: list[VNode] = []
                for selector in node.selectors:  # These are the <selectors> from ..[<selectors>]
                    #selector = cast(SelectorNode, selector_ast_node)
                    
                    # Apply this individual selector to temp_input_for_selectors
                    descendant_segment_context = Context("<descendant_segment>", context, node.position )
                    descendant_segment_context.set_symbol(SEGMENT_INPUT_NODELIST_KEY, temp_input_for_selectors)
                
                    current_selector_output: VNodeList = rt_res.register(self.visit(selector, descendant_segment_context))
                    if rt_res.error: return rt_res
                
                    if current_selector_output:  # VNodeList might be empty
                        # exclude cycle nodes
                        cycle_nodes = [node for node in current_selector_output.node_list if not id(node.jvalue) in instance_ids]
                        # ri_for_this_di.extend(current_selector_output.node_list)
                        ri_for_this_di.extend(cycle_nodes)

            
            # Now, ri_for_this_di is complete (it's Ri).
                # Add it to the list that accumulates R values for the current_d1_vnode.
                r_values_for_current_d1.extend(ri_for_this_di)
            
            # After iterating through all Di in the sequence for current_d1_vnode,
            # r_values_for_current_d1 now holds (R1 + ... + Rn) for that current_d1_vnode.
            # Add these to the overall segment results.
            overall_segment_results.extend(r_values_for_current_d1)
        
        # After processing all nodes from the input_vnodelist,
        # overall_segment_results contains the final concatenated list.
        return rt_res.success(VNodeList(overall_segment_results))
    
    
    def visit_SegmentNode(self, node: SegmentNode, context: Context) -> RuntimeResult:
        """A segment contains one or more Selectors"""
        rt_res = RuntimeResult()
        if node.node_type == ASTNodeType.DESCENDANT_SEGMENT:
            return self.visit_DescendantSegment(node, context)
        
        output_nodelist: VNodeList = VNodeList([])
        for selector in node.selectors:
            selector_output:VNodeList = rt_res.register(self.visit(selector, context))
            if rt_res.error: return rt_res
            output_nodelist.extend(selector_output)
        return rt_res.success(output_nodelist)
        
    
    def visit_NameSelectorNode(self, node: NameSelectorNode, context: Context) -> RuntimeResult:
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = context.get_symbol(SEGMENT_INPUT_NODELIST_KEY)
        if input_nodelist is None:
            # todo after testing convert this exception to a logging error msg.
            raise ValueError(f"No input nodelist '{SEGMENT_INPUT_NODELIST_KEY}' found in Context for {node}")
        if not input_nodelist:
            return rt_res.success(VNodeList([]))  # no input nodes, so nothing to select
        
        output_nodelist: list[VNode]  = []
        input_node: VNode
        for input_node in input_nodelist:
            if isinstance(input_node.jvalue, JSON_OBJECT_TYPES):
                jpath  = input_node.jpath
                jvalue_dict = input_node.jvalue
                if node.member_name in jvalue_dict:
                    output_nodelist.append(
                        VNode( NormalizedJPath(f"{jpath}['{node.member_name}']"), jvalue_dict[ node.member_name ],
                               input_node.root_value, input_node.node_depth +1 )
                    )
                
        return rt_res.success(VNodeList(output_nodelist))
        
    def visit_WildcardSelectorNode(self, node: WildcardSelectorNode, context: Context) -> RuntimeResult:
        """Wildcard selector selects all child nodes of each node in the input nodelist.
        Children are either dict values or list elements. Nothing is selected for JSON primitives."""
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = context.get_symbol(SEGMENT_INPUT_NODELIST_KEY)
        if input_nodelist is None:
            # todo after testing convert this exception to a logging error msg.
            raise ValueError(f"No input nodelist '{SEGMENT_INPUT_NODELIST_KEY}' found in Context for {node}")
        if not input_nodelist:
            return rt_res.success(VNodeList([]))  # no input nodes, so nothing to select
        
        output_nodelist: list[VNode] = []
        input_node: VNode
        for input_node in input_nodelist:
            output_nodelist.extend(self._children_of(input_node))
        
        return rt_res.success(VNodeList(output_nodelist))
    
    
    def visit_SliceSelectorNode(self, node: SliceSelectorNode, context: Context) -> RuntimeResult:
        """Apply the slice to every element of the input_nodelist and return the resulting node_list. """
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = context.get_symbol(SEGMENT_INPUT_NODELIST_KEY)
        if input_nodelist is None:
            # todo after testing convert this exception to a logging error msg.
            raise ValueError(f"No input nodelist '{SEGMENT_INPUT_NODELIST_KEY}' found in Context for {node}")
        if not input_nodelist:
            return rt_res.success(VNodeList([]))  # no input nodes, so nothing to select
        
        output_nodes: list[VNode] = []
        input_node: VNode
        current_slice_obj = node.slice_op
        for input_node in input_nodelist:
            if not isinstance(input_node.jvalue, JSON_ARRAY_TYPES):
                continue
            jpath = input_node.jpath
            jvalue_list = input_node.jvalue
            length:int = len(jvalue_list)
            if length == 0 or current_slice_obj.step == 0: continue
            # See 2.3.4.2.2. Normative Semantics, pg 23, RFC 9535
            actual_start, actual_stop, actual_step = current_slice_obj.indices(length)
            # Iterate using the original indices
            for original_idx in range(actual_start, actual_stop, actual_step):
                selected_element = jvalue_list[original_idx]
                
                # Construct the new path for the selected element
                # Assuming input_vnode.jpath is a NormalizedJPath object with a __str__ method
                new_path_str = f"{str(jpath)}[{original_idx}]"
                
                new_vnode = VNode(NormalizedJPath(new_path_str), selected_element,
                                  input_node.root_value, input_node.node_depth +1 )
                output_nodes.append(new_vnode)
        
        return rt_res.success(VNodeList(output_nodes))

        
    def visit_IndexSelectorNode(self, node: IndexSelectorNode, context: Context) -> RuntimeResult:
        """Apply self.index to every element of the input_nodelist and return the resulting VNodeList."""
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = context.get_symbol(SEGMENT_INPUT_NODELIST_KEY)
        if input_nodelist is None:
            # todo after testing convert this exception to a logging error msg.
            raise ValueError(f"No input nodelist '{SEGMENT_INPUT_NODELIST_KEY}' found in Context for {node}")
        if not input_nodelist:
            return rt_res.success(VNodeList([]))  # no input nodes, so nothing to select
        
        ouput_nodes: list[VNode] = []
        input_node: VNode
        for input_node in input_nodelist:
            if not isinstance(input_node.jvalue, JSON_ARRAY_TYPES):
                continue
            jpath = input_node.jpath
            jvalue = input_node.jvalue
            length = len(jvalue)
            if length == 0: continue
            index_normal = normalize_list_index( node.index, length )
            if 0 <= index_normal < length:
                new_node = VNode( NormalizedJPath( f"{jpath}[{index_normal}]" ), jvalue[index_normal],
                                  input_node.root_value, input_node.node_depth + 1 )
                ouput_nodes.append(new_node)
                
        return rt_res.success(VNodeList(ouput_nodes))
    
    def visit_FilterSelectorNode_current(self, node: FilterSelectorNode, context: Context) -> RuntimeResult:
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = context.get_symbol(SEGMENT_INPUT_NODELIST_KEY)
        if input_nodelist is None:
            # todo after testing convert this exception to a logging error msg.
            # For now, let's be strict during development
            _logger.error(f"No input nodelist '{SEGMENT_INPUT_NODELIST_KEY}' found in Context for {node}")
            return rt_res.failure(RTError(node.position, f"Internal error: No input nodelist for filter.", context))
        
        if input_nodelist.is_empty():
            return rt_res.success(VNodeList([]))  # no input nodes, so nothing to select
        
        output_nodes: list[VNode] = []
        logical_expr_node: ASTNode = node.logical_expr_node
        
        # Create a context for evaluating the logical expression.
        # This context will be reused, but CURRENT_NODE_KEY will be updated in the loop.
        # The position for errors within the logical expression should come from logical_expr_node
        filter_eval_context = Context("<filter_expression>", context, logical_expr_node.position)
        
        for current_tested_node in input_nodelist: # This 'current_tested_node' is the node to which the filter applies
            
            # Set '@' for the logical expression to be the current_tested_node itself
            filter_eval_context.set_symbol(CURRENT_NODE_KEY, current_tested_node)
            
            # Evaluate the logical expression (e.g., @.price != 8.99)
            # The result should be a BooleanValue
            eval_result: BooleanValue = rt_res.register(self.visit(logical_expr_node, filter_eval_context))
            
            if rt_res.error:
                _logger.error(f"Error evaluating filter expression for node {current_tested_node.jpath}: {rt_res.error}")
                # Option 1: Treat as false and continue (common for filters)
                # continue
                # Option 2: Propagate the error (stops the whole query for this path)
                return rt_res # Propagate error
            
            if not isinstance(eval_result, BooleanValue):
                err_msg = f"Filter predicate for {current_tested_node.jpath} evaluated to non-boolean type {type(eval_result).__name__}"
                _logger.error(err_msg)
                return rt_res.failure(RTError(logical_expr_node.position, err_msg, filter_eval_context))
            
            # If the logical expression is true for current_tested_node, add current_tested_node to the output
            if eval_result.value: # .value gives the Python bool from BooleanValue
                output_nodes.append(current_tested_node)
        
        return rt_res.success(VNodeList(output_nodes))
        
    def visit_FilterSelectorNode(self, node: FilterSelectorNode, context: Context) -> RuntimeResult:
        """Acts as a predicate for selecting input nodes. If the filter selector evaluates to logical True for
        the input node, then the input node is added to the output nodelist.
        
        2.3.5.2. Semantics, pg 28, RFC 9535
        The filter selector works with arrays and objects exclusively. Its result is a list of (zero, one, multiple,
        or all) their array elements or member values, respectively. Applied to a primitive value, it selects nothing
        (and therefore does not contribute to the result of the filter selector).
        
        """
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = context.get_symbol(SEGMENT_INPUT_NODELIST_KEY)
        if input_nodelist is None:
            # todo after testing convert this exception to a logging error msg.
            raise ValueError(f"No input nodelist '{SEGMENT_INPUT_NODELIST_KEY}' found in Context for {node}")
        if input_nodelist.is_empty():
            return rt_res.success(VNodeList([]))  # no input nodes, so nothing to select
        
        input_node: VNode
        include_node: BooleanValue
        output_nodes: list[VNode] = []
        logical_expr_node: ASTNode = node.logical_expr_node
        filter_sel_context = Context("<filter_selector>", context, node.position )
        
        for input_node in input_nodelist:
            if isinstance(input_node.jvalue, JSON_PRIMITIVE_TYPES):
                continue  # filter selector only applies to arrays and objects
            filter_sel_context.set_symbol(FILTER_SELECTOR_INPUT_NODE_KEY, input_node)
            if isinstance(input_node.jvalue, JSON_ARRAY_TYPES):
                for index, value in enumerate(input_node.jvalue):
                    current_node = VNode(NormalizedJPath(f"{input_node.jpath}[{index}]"), value,
                                         input_node.root_value, input_node.node_depth + 1 )
                    filter_sel_context.set_symbol(CURRENT_NODE_KEY, current_node)
                    include_node  = rt_res.register(self.visit(logical_expr_node, filter_sel_context))
                    # if the logical_expr returns LogicalTrue, add the current_node to the output nodelist
                    if rt_res.error:
                        _logger.error(rt_res.error)
                        
                    if isinstance(include_node, VNodeList):
                        if not include_node.is_empty():
                            output_nodes.append(current_node)  # existence test passed
                    elif isinstance(include_node, (bool, BooleanValue, LogicalType)):
                        if include_node:
                            output_nodes.append(current_node)
                    elif include_node == Nothing:
                        pass  # we don't include the current node
                    elif include_node or include_node.value == True:
                        output_nodes.append(current_node)
                        
            elif isinstance(input_node.jvalue, JSON_OBJECT_TYPES):
                for member_name, member_value in input_node.jvalue.items():
                    current_node = VNode(
                        NormalizedJPath(f"{input_node.jpath}['{member_name}']"), member_value,
                                        input_node.root_value, input_node.node_depth + 1  )
                    filter_sel_context.set_symbol(CURRENT_NODE_KEY, current_node)
                    include_node = rt_res.register(self.visit(logical_expr_node, filter_sel_context))
                    # if the logical_expr returns LogicalTrue, add the current_node to the output nodelist
                    if rt_res.error:
                        _logger.error(rt_res.error)
                      
                    if isinstance(include_node, VNodeList):
                        if not include_node.is_empty():
                            output_nodes.append(current_node)  # existence test passed
                    elif isinstance(include_node, (bool, BooleanValue, LogicalType)):
                        if include_node:
                            output_nodes.append(current_node)
                    elif include_node == Nothing:
                        pass  # we don't include the current node
                    elif include_node or include_node.value == True:
                        output_nodes.append(current_node)
            else:
                _logger.error(f"Unsupported value type '{type(input_node.jvalue) }'")
                raise ValueError(f"Unsupported value type '{type(input_node.jvalue)}'")

        return rt_res.success(VNodeList(output_nodes))


    def visit_RelativeQueryNode(self, node: RelativeQueryNode, context: Context) -> RuntimeResult:
        """Return the resulting output VNodeList in RuntimeResult.value
        
        """
        rt_res = RuntimeResult()
        current_node: VNode = context.get_symbol(CURRENT_NODE_KEY)
        if current_node is None:
            # todo after testing convert this exception to a logging error msg.
            raise ValueError(f"No current node '{CURRENT_NODE_KEY}' found in Context for {node}")
        
        segments: RepetitionNode = node.segments
        input_nodelist: VNodeList = VNodeList([current_node])
    
        if segments.is_empty():
            # no segments in the relative query, so we just return the current node
            return rt_res.success(input_nodelist)
        
        """Evaluating all these segments in a chain from input-> output VNodeLists result in a final output nodelist.
        This node list is evaluated for truthiness as an existence test or to compare to another logical_expr
        """
        segment_output: VNodeList = input_nodelist  # default, in case there are no segments
        for seg_node in segments:
            # creating a new Context provides a local scope for the segment visit
            rel_query_context = Context("<rel_query>", context, seg_node.position )
            rel_query_context.set_symbol(SEGMENT_INPUT_NODELIST_KEY, input_nodelist)
            segment_output = rt_res.register(self.visit(seg_node, rel_query_context))
            if rt_res.error:
                _logger.error(rt_res.error)
                continue  # todo should we break here instead of just continue? What do we get by skipping a segment?
            if not isinstance(segment_output, VNodeList):
                raise TypeError(f"visit_RelativeQueryNode: visit seg_node returned Unsupported value type '{type(segment_output)}'")
            input_nodelist = segment_output   # output of this segment becomes input for the next segment
        
        return rt_res.success(segment_output)


    def visit_RelativeSingularQueryNode(self, node: RelativeSingularQueryNode, context: Context) -> RuntimeResult:
        """Evaluate the segment chain starting from the current node through the child segments and return
        the output VNodeList in RuntimeResult.value. It will contain either one or zero VNnode elements. """
        rt_res = RuntimeResult()
        current_node: VNode = context.get_symbol(CURRENT_NODE_KEY)
        segments = node.segments
        if segments.is_empty():
            # if no segments, we just return the current node
            return rt_res.success(VNodeList([current_node]))
        
        input_nodelist: VNodeList = VNodeList([current_node])
        segment_ouput: VNodeList = input_nodelist  # default, in case there are no segments
        for seg_node in node.segments:
            # creating a new Context provides a local scope for the segment visit
            seg_context = Context("<singular_query_segment>", context, seg_node.position )
            seg_context.set_symbol(SEGMENT_INPUT_NODELIST_KEY, input_nodelist)
            segment_ouput = rt_res.register(self.visit(seg_node, seg_context))
            if rt_res.error: return rt_res # todo we're not supposd to raise errors, just ignore this segment?
            input_nodelist = segment_ouput   # output of this segment becomes input for the next segment
        
        return rt_res.success(segment_ouput)
        
    def visit_AbsoluteSingularQueryNode(self, node: AbsoluteSingularQueryNode, context: Context) -> RuntimeResult:
        """Evaluate the segment chain starting from the current node through the child segments and return
        the output VNodeList in RuntimeResult.value. It will contain either one or zero VNnode elements. """
        rt_res = RuntimeResult()
        input_nodelist: VNodeList = rt_res.register(self.visit_RootNode(node.root_node, context))
        if rt_res.error: return rt_res
        segments = node.segments
        if segments.is_empty():
            # if no segments, we just return the current node
            return rt_res.success(input_nodelist)
        
        segment_ouput: VNodeList = input_nodelist  # default, in case there are no segments
        for seg_node in node.segments:
            # creating a new Context provides a local scope for the segment visit
            seg_context = Context("<singular_query_segment>", context, seg_node.position )
            seg_context.set_symbol(SEGMENT_INPUT_NODELIST_KEY, input_nodelist)
            segment_ouput = rt_res.register(self.visit(seg_node, seg_context))
            if rt_res.error: return rt_res # todo we're not supposd to raise errors, just ignore this segment?
            input_nodelist = segment_ouput   # output of this segment becomes input for the next segment
        
        return rt_res.success(segment_ouput)

    def visit_FunctionCallNode(self, node: FunctionCallNode, context: Context) -> RuntimeResult:
        """Evaluate the function and return its return value, which can be a ValueType, LogicalType, or NodesType """
        rt_res = RuntimeResult()
        if not isinstance(node, FunctionCallNode):
            raise TypeError(f"Expected FunctionCallNode, got '{type(node)}'")
        
        # we must evaluate each argument and call the function's eval method for it.
        func_args = node.func_args
        arg: FunctionArgument
        func_name = node.func_node.func_name
        func_context = Context(f"{func_name}()", context, context.parent_entry_pos)
        # we could add the argument to the context and let the function retrieve values from the context. but here
        # we just call directly with the kwargs dict.
        call_args: list[Any] = []
        for fa in func_args:
            arg = cast(FunctionArgument, fa)
            arg_value = rt_res.register(self.visit(arg.arg_node, func_context))
            if rt_res.error: raise ValueError(rt_res.error)
            # We need logic to translate the fa to a compatible type for the function. Some functions need a VNodeList,
            # some just want the singular value from the VNode in a 1-item VNodeList.
            
            call_args.append(arg_value)
        
        kwargs: dict[str, Any] = {}
        params = node.func_node.param_list
        for  index, item in enumerate(call_args):
            kwargs[params[index].param_name] = item
        
        # todo - this should be wrapped with a try/except block so we can continue gracefully in case of an error
        func_value = node.func_node.eval(**kwargs)  # method call happens here
        
        return rt_res.success(func_value)
    
    # noinspection GrazieInspection
    def visit_UnaryOpNode(self, node: UnaryOpNode, context: Context) -> RuntimeResult:
        """The only use of this node is to invert the truth value of a logical_expr in a test_expr and paren_expr:
        
        test_expr  ::=  [ "!" ] ( filter_query | function_expr )
        
        paren_expr  ::=  [ "!" ] "(" logical_expr ")"
        
        """
        rt_res = RuntimeResult()
        if node.node_type == ASTNodeType.LOGICAL_NOT:
            result_node = rt_res.register( self.visit(node.node, context ))
            bool_flag: BooleanValue
            if isinstance(result_node, VNodeList):
                if result_node.is_empty():
                    bool_flag = BooleanValue(False)
                else:
                    bool_flag = BooleanValue(True)
            else:
                bool_flag = rt_res.register( self.visit(node.node, context ))
            negated_flag = bool_flag.negate()
            return rt_res.success(negated_flag)
        raise TypeError(f"Unsupported type '{type(node.node_type)}', expected ASTNodeType.LOGICAL_NOT")
        
    # Helper method for visit_BinaryOpNode to get a comparable value from an evaluation result
    # (handles VNodeLists by taking their single value, or EvaluatorValue wrappers/raw JSON_VALUEs)
    def get_comparable_value( self,
                              eval_result:      ComparableType,
                              ast_node_for_pos: ASTNode,
                              context:          Context
                             ) -> tuple[ ComparableType , Error | None ]:
        
        if isinstance(eval_result, VNodeList):
            if len(eval_result) == 1:
                # VNode.jvalue is a raw JSON_ValueType. _unwrap in compare_ops.py handles raw JSON_VALUEs
                # and also EvaluatorValue wrappers if VNode.jvalue happened to be one.
                return eval_result.node_list[0].jvalue, None
            elif len(eval_result) == 0:
                # An empty nodelist, often treated as 'Nothing' in JSONPath.
                # Comparisons with Nothing are typically false or undefined.
                # We'll pass Nothing, and compare_ops.eval should handle it (likely returning None).
                return Nothing, None # Nothing is from json_type_defs.py
            else: # More than one node
                err = RTError(  ast_node_for_pos.position,
                         f"Nodelist with {len(eval_result)} elements cannot be directly used in this comparison."
                                f" Expected a single value or empty.",
                                context
                              )
                return None, err
        # Check if it's an EvaluatorValue wrapper (like NumberValue) or a raw JSON_ValueType
        elif isinstance(eval_result, (EvaluatorValue, *JSON_VALUE_TYPES)):
            return eval_result, None
        # If the result of a sub-expression was already a LogicalType (e.g., from another comparison or NOT)
        elif isinstance(eval_result, LogicalType):
            # For comparison, we'd use its underlying bool if comparing against another bool.
            # For AND/OR, we use LogicalType directly.
            return eval_result.value, None # Unwrap to Python bool for comparison
        elif eval_result == Nothing:
            return eval_result, None
        else:
            err = RTError(ast_node_for_pos.position,
                          f"Unexpected type for operand: {type(eval_result).__name__}",
                          context)
            return None, err
   
        
    def visit_BinaryOpNode(self, node: BinaryOpNode, context: Context) -> RuntimeResult:
        rt_res = RuntimeResult()
        left_node  = node.left_node
        right_node = node.right_node
        # Evaluate the left operand
        left_eval_result = rt_res.register(self.visit(left_node, context))
        if rt_res.error: return rt_res
        
        # Evaluate the right operand
        right_eval_result = rt_res.register(self.visit(right_node, context))
        if rt_res.error: return rt_res
        
        op_token_type = node.op_token.token_type
        
        # Handle comparison operators
        if op_token_type not in COMPARISON_OP_TYPE_LOOKUP:
            return rt_res.failure(RTError(node.op_token.position,
                                          f"Unsupported binary operator: {op_token_type}",
                                          context))
        

        comparison_op = COMPARISON_OP_TYPE_LOOKUP[op_token_type]
        actual_left_operand, error = self.get_comparable_value(left_eval_result, left_node, context )
        if error: return rt_res.failure(error)
        
        actual_right_operand, error = self.get_comparable_value(right_eval_result, right_node, context )
        if error: return rt_res.failure(error)
        
        # `actual_left_operand` and `actual_right_operand` are now EvaluatorValue wrappers,
        # raw JSON_VALUEs, or the Nothing object.
        # `compare_ops.eval` needs to handle these (especially Nothing).
        comparison_result: BooleanValue = comparison_op.eval(actual_left_operand, actual_right_operand)
        
        if comparison_result is None:
            raise ValueError(f"Comparison evaluation failed for {op_token_type}. Node: {node!r} ")
        
        comp_pos = Position(left_node.position.text, left_node.position.start, right_node.position.end)
        comparison_result.set_context(context).set_pos(comp_pos)
        return rt_res.success(comparison_result)
    
    
    def visit_RepetitionNode(self, node: RepetitionNode, context: Context) -> RuntimeResult:
        """We use a RepetitionNode for evaluating logical_and_expr and logical_or_expr in this context. This is to
        avoid having to create another ASTNode for each, however, that might make more sense. This is in progress.
        Also, we implement these as a list of nodes instead of nested binary nodes so we can short-circuit evaluation
        at the top level of node evaluation.
        """
        rt_res = RuntimeResult()
        if not isinstance(node, RepetitionNode):
            raise TypeError(f"Expected RepeitionNode, got {type(node).__name__}")
        
        if node.node_type not in (ASTNodeType.LOGICAL_AND_EXPR, ASTNodeType.LOGICAL_OR_EXPR):
            raise TypeError(f"Expected LOGICAL_AND_EXPR or LOGICAL_OR_EXPR, got {node.node_type}")
        
        node_type = node.node_type
        current_bool_result: bool | None = None
        for logical_node in node:
            eval_result = rt_res.register(self.visit(logical_node, context))
            if rt_res.error: return rt_res
            if eval_result is None:
                raise ValueError(f"eval result is None for {logical_node!r}")
                
            bool_for_node: bool
            if isinstance(eval_result, VNodeList):
                bool_for_node = False if eval_result.is_empty() else True
            elif isinstance(eval_result, BooleanValue):
                bool_for_node = eval_result.value
            else:
                raise TypeError(f"eval_result is {type(eval_result).__name__}")
                
            if node_type == ASTNodeType.LOGICAL_AND_EXPR:
                current_bool_result = current_bool_result and bool_for_node if current_bool_result else bool_for_node
                if current_bool_result == False:
                    break  # short circuit
            else:
                current_bool_result = current_bool_result  or bool_for_node if current_bool_result else bool_for_node
                # noinspection PySimplifyBooleanCheck
                if current_bool_result == True:
                    break  # short circuit
        
        if current_bool_result is None:
            raise ValueError(f"current_bool_result is None after visiting {node!r}")
        return rt_res.success(BooleanValue.value_for(current_bool_result))
    
    def visit_NumericLiteralNode(self, node: NumericLiteralNode, context: Context) -> RuntimeResult:
        rt_res = RuntimeResult()
        if not isinstance(node, NumericLiteralNode):
            raise TypeError(f"Unsupported type '{type(node.node_type)}', expected NumericLiteralNode")
        number_value = NumberValue(node.value ).set_context(context).set_pos(node.position)
        return rt_res.success(number_value)
    
    def visit_StringLiteralNode(self, node: StringLiteralNode, context: Context) -> RuntimeResult:
        rt_res = RuntimeResult()
        if not isinstance(node, StringLiteralNode):
            raise TypeError(f"Unsupported type '{type(node.node_type)}', expected StringLiteralNode")
        string_value = StringValue(node.raw_string).set_context(context).set_pos(node.position)
        return rt_res.success(string_value)
    
    def visit_BooleanLiteralNode(self, node: BooleanLiteralNode, context: Context) -> RuntimeResult:
        rt_res = RuntimeResult()
        if not isinstance(node, BooleanLiteralNode):
            raise TypeError(f"Unsupported type '{type(node.node_type)}', expected BooleanLiteralNode")
        bool_value = BooleanValue( node.value ).set_context(context).set_pos(node.position)
        return rt_res.success(bool_value)
        
    def visit_NullLiteralNode(self, node: NullLiteralNode, context: Context) -> RuntimeResult:
        rt_res = RuntimeResult()
        if not isinstance(node, NullLiteralNode):
            raise TypeError(f"Unsupported type '{type(node.node_type)}', expected NullLiteralNode")
        null_value = NullValue().set_context(context).set_pos(node.position)
        return rt_res.success(null_value)
 
 
    ####################################################################
    # SUBQUERY EVAL METHODS
    ####################################################################
    
    """
    These methods are never executed during evaluation of a well-formed json path query string, i.e., one that starts
    with the root node identifier $. These methods exist to support testing of arbitrary grammar productions, to
    allow ASTNodes generated from the parser's subparse() method to be evaluated for a value and returned.
    """
    
    def visit_IdentifierNode(self, node: IdentifierNode, context: Context ) -> RuntimeResult:
        rt_res = RuntimeResult()
        if not isinstance(node, IdentifierNode):
            raise TypeError(f"Unsupported type '{type(node.node_type)}', expected IdentifierNode")
        
        # we have to add quotes because the StringValue expects parsed strings to be quoted,
        # thus it removes the first and last characters of the argument string when saving the string's value.
        str_value = f"'{node.value}'"
        id_str = StringValue(str_value).set_context(context).set_pos(node.position)
        return rt_res.success(id_str)
    
    
    
####################################################################
# SLICE HELPER METHODS
####################################################################
# These are defined per RFC 9535, but our slice implementation currently just uses Python's native list slicing operator

class SliceBounds(NamedTuple):
    lower:     int
    upper:     int
    step:      int
    array_len: int


def normalize_slice_parameter(slice_parameter: int, array_len: int ) -> int:
    """Slice expression parameters `start` and `end` are not directly usable as slice bounds and must first be
    normalized. (RCF 9535 page 23).

    """
    return slice_parameter if slice_parameter >= 0 else ( array_len + slice_parameter )


def slice_bounds(start: int, end: int, step: int, array_len: int) -> SliceBounds:
    """Return a tuple of slice bounds (start, end, step) that are usable as slice bounds.
    (RCF 9535 page 24).
    """
    start_normal = normalize_slice_parameter(start, array_len)
    end_normal   = normalize_slice_parameter(end, array_len)
    
    if step >= 0:
        lower = min( max(start_normal, 0), array_len)
        upper = min( max(end_normal,   0), array_len)
    else:
        upper = min( max(start_normal, -1), array_len - 1)
        lower = min( max(end_normal,   -1), array_len - 1)
    
    return SliceBounds(lower, upper, step, array_len)


def normalize_list_index(list_index: int, array_len: int) -> int:
    """Return the original list index if list_index is zero or positive, or convert a negative list index
    to be a positive index from the start of the list. """
    return normalize_slice_parameter(list_index, array_len)
 
 
