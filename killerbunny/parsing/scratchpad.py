#  File: scratchpad.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#
#

"""Module for holding snippets of code I want to removed from a module, but don't want to delete quite yet in case I
decide to re-use them"""

from killerbunny.parsing.node_type import ASTNode


#from killerbunny.parsing.node_type import ASTNode, ASTNodeType


class SegmentNode(ASTNode):
    pass


class SegmentListNode(ASTNode):
    """This serves as a node in the linked list of segments. It has references to the previous and next segment nodes,
    and the payload is a Node.
    """
    def __init__(self, segment: SegmentNode,
                 prev_segment: 'SegmentListNode | None' = None,
                 next_segment: 'SegmentListNode | None' = None) -> None:
        
        super().__init__(ASTNodeType.UNKNOWN)
        self.prev_segment: SegmentListNode  | None = prev_segment
        self.next_segment: SegmentListNode  | None = next_segment
        self.segment: SegmentNode = segment
        
    def add_new_segment(self, segment: SegmentNode) -> 'SegmentListNode':
        """Create a new SegmentListNode using the provided segment as the node's payload value, and add it
        to this doubly-linked list.
        The new node's prev_segment will be set to this(self) SegmentListNode.
        This(self) node's next_segment will be set to the new SegmentListNode.
        In the context of parsing JSONPath queries, this SegmentListNode is normally the tail of the linked list.
        But for completeness, all pointers are updated as expected.
        E.g., given the list Aa <-> Bb <-> Cc, (upper case are the SegmentListNodes and lower case are the "payload"
        values) and you are calling B.add_new_segment(d), this results in the list modified to become
        Aa <-> Bb <-> Dc <-> Cc
        Returns the new SegmentListNode.
        """
        new_segment: SegmentListNode
        if self.next_segment is not None:
            # Aa <-> Cc , self is A in this diagram
            saved_next_segment: SegmentListNode  = self.next_segment  # -> Cc save current next node pointer
            new_segment = SegmentListNode(segment, prev_segment=self, next_segment=saved_next_segment)  #  Aa <- Bb -> C
            self.next_segment = new_segment  # Aa <-> Bb -> C
            saved_next_segment.prev_segment = new_segment # Aa <-> Bb <-> C
        else:
            new_segment = SegmentListNode(segment, prev_segment=self)
            self.next_segment = new_segment
        return new_segment


HEAD_NODE = SegmentListNode(SegmentNode())  # always the head of the linked list of SegmentListNodes
