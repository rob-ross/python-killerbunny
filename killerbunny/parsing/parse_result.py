#  File: parse_result.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

from killerbunny.shared.errors import Error
from killerbunny.parsing.node_type import ASTNode


####################################################################
# PARSE RESULT
####################################################################

# noinspection GrazieInspection
class ParseResult:
    """Manages error detection and reporting across recursively nested grammar productions.
    Usage:
    
    1. Initialize a ParseResult at the start of a grammar production method.
        E.g., production rule: foo ::= $ bar
        
        def foo(self):
            res = ParseResult()
            ...
            
    2.  When consuming a token in the production method, use res.register_advancement() with self.advance():
    
        def foo(self):
            res = ParseResult()
            if current_token == $:
                res.register_advancement()
                self.advance()
                
    3. When calling a sub-production method (like `bar` above), wrap the call in a res.register() call
            ...
            node = res.register(self.bar())
    
    4. Check for error after calling res.register():
            ...
            node = res.register(self.bar())
            if res.error return res # abort production rule and propogate Error up the call stack
    
    5. If a parse error occurs in the current parse method, return res.failure()
    
            def foo(self):
                res = ParseResult()
                if current_token != $:
                    res.failure(SomeErrorClass(error_position, "Expected $"))
    
    6. If the happy path is reached, return res.success() with the object (usually a node) to be returned to the caller
    
            def foo(self):
                res = ParseResult()
                ...
                node = res.register(self.bar())
                if res.error return res
                # assuming parse succeeded here:
                return res.success(node)
                # can also use return res.success(None) to indicate success without a return object
                
    7. If a production may or may not be expected to successfully parse, use try_register(). This attempts to parse.
        If successful (i.e., no Error) works just like res.register(). If an Error occurrs, it returns None and
        sets internal state `to_reverse_count` to allow backtracking.
        
        def foo(self):
            res = ParseResult()
            ...
            logical_expr = res.try_register(self.logical_expr())
            if logical_expr is None:
                self.backtrack(res.to_reverse_count) # restore state as it was before trying logical_expr()
                ...
                literal_node = res.register(self.string_literal()) # try a different production rule
                ...
            
                
    General notes:
    --------------
    1. Call res.register_advancement() in a production method every time that method itself successfully consumes
        a token using self.advance().
    2. When a production method detects an error specific to its own rule
        (e.g., expected a specific token but found another), call res.failure(SpecificError(...)).
    3. Rely on res.register() to propagate errors from deeper levels.
        The logic within register and failure will generally ensure that the error reported at the top level
        is the one that occurred at the earliest significant point of failure.
    4. At the very top level of your parser (e.g., in your main parse() or start() method), check res.error.
        If it's set, that's the error to report to the user.
    5. When several productions are possible, use res.try_register(). If it returns None, the parsing failed. Call
        self.backtrack(res.to_reverse_count)
        and then try the next production.
    
    This system is designed to prevent generic error messages from higher-level productions from masking
    more specific errors from lower-level ones, especially once a higher-level production
    has already made some successful parsing steps.
    
    """
    def __init__(self) -> None:
        self.error: Error | None = None
        self._node: ASTNode |  None  = None
        self.last_registered_advance_count = 0
        self.advance_count: int = 0
        self._to_reverse_count = 0


    @property
    def node(self) -> ASTNode |  None:
        return self._node
    
    @property
    def to_reverse_count(self) -> int:
        return self._to_reverse_count
    
    def register_advancement(self) -> None:
        self.last_registered_advance_count = 1
        self.advance_count += 1
    
    def register(self, result: 'ParseResult') -> ASTNode |  None :
        self.last_registered_advance_count = result.advance_count
        self.advance_count += result.advance_count
        if result.error: self.error = result.error
        return result.node

    def try_register(self, result: 'ParseResult') -> ASTNode |  None:
        if result.error:
            self._to_reverse_count = result.advance_count
            return None
        return self.register(result)
    
    def success(self, node: ASTNode |  None) -> 'ParseResult':
        self._node = node
        return self
    
    
    def failure(self, error: Error) -> 'ParseResult':
        if not self.error or self.last_registered_advance_count == 0:
            self.error = error
        return self