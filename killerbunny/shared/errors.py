#  File: errors.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

import inspect
import os
import sys
from types import FrameType
from typing import override

from killerbunny.shared.context import Context
from killerbunny.shared.position import Position


####################################################################
# ERRORS
####################################################################

class Error:
    def __init__(self, position: Position, error_name: str, details: str, originating_method_name: str | None = None) -> None:
        self.error_name: str = error_name
        self.details = details
        self.position: Position = position
        if originating_method_name is None:
            # This __init__ method is one frame.
            # Its caller (e.g., InvalidSyntaxError.__init__ or the actual instantiating method) is another.
            # We want to find the method that *called* into the Error hierarchy's __init__ chain.
            
            # Get the frame of Error.__init__ itself
            error_init_frame: FrameType | None = inspect.currentframe()
            
            # The frame that called Error.__init__ is error_init_frame.f_back
            # This is the starting point for our search upwards.
            initial_caller_frame = error_init_frame.f_back if error_init_frame else None
            
            self.originating_method_name = self._determine_originating_method(initial_caller_frame)
            
            # It's good practice to delete frame objects if assigned to local variables
            # to help break potential reference cycles, especially if inspect.currentframe() is used.
            if error_init_frame:
                del error_init_frame
        else:
            self.originating_method_name = originating_method_name
        
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.error_name}: {self.details})'
    
    def as_string(self) -> str:
        details_str = self.details if self.details else ''
        origin_str = self.originating_method_name if self.originating_method_name else ''
        err_str = self.error_name
        msg = ': '.join([err_str, origin_str, details_str])
        result  = f'{msg} at position {self.position.start + 1}\n'
        result += indicator_string(self.position.text, self.position)
        return result
    
    def as_test_string(self) -> str:
        """For use in unit testing. Changes to this method may break unit tests"""
        details_str = self.details if self.details else ''
        origin_str = self.originating_method_name if self.originating_method_name else ''
        err_str = self.error_name
        msg = ': '.join([err_str, origin_str, details_str])
        result  = f'{msg} at position {self.position.start + 1}: '
        result += indicator_string(self.position.text, self.position, use_color=False)
        return result
    
    def _determine_originating_method(self, frame: FrameType | None) -> str:
        """
        Walks up the call stack starting from 'frame' (which should be the
        immediate caller of Error.__init__) and returns the name of the first
        function/method that is not an __init__ method of Error or its subclasses.
        """
        current_search_frame= frame
        try:
            while current_search_frame:
                func_name = current_search_frame.f_code.co_name
                
                # Check if this frame is an __init__ of Error or its subclasses
                if func_name == "__init__":
                    # Get 'self' from the frame's local variables to check its class
                    instance_self = current_search_frame.f_locals.get('self')
                    if instance_self is not None and isinstance(instance_self, Error):
                        # This is an __init__ method of Error or one of its subclasses.
                        # We want to go further up the stack.
                        current_search_frame = current_search_frame.f_back
                        continue # Move to the next frame up
                
                # If we are here, it means the current frame is:
                #   - Not an __init__ method, OR
                #   - An __init__ method of a class not in the Error hierarchy.
                # This should be the frame where the Error instance was created.
                return func_name
            
            return "<module_or_unknown>" # Stack unwound completely, error likely at module level
        except Exception:
            # Catch any introspection errors (e.g., accessing f_code, f_locals)
            return "<introspection_error>"
        finally:
            # Clean up the frame reference used in the loop
            if 'current_search_frame' in locals() and current_search_frame is not None:
                del current_search_frame
                
                

class IllegalCharError(Error):
    def __init__(self, position: Position, details: str) -> None:
        super().__init__(position, 'Illegal Character', details)

class UnbalancedCharError(Error):
    def __init__(self, position: Position, error_name:str, details: str) -> None:
        super().__init__(position, error_name, details)
        
class InvalidSyntaxError(Error):
    def __init__(self, position: Position, details:str = '') -> None:
        super().__init__(position, 'Invalid Syntax', details)
        

class IllegalFunction(Error):
    def __init__(self, position: Position, details:str = '') -> None:
        super().__init__(position, 'Illegal Function Name', details)
      

class ValidationError(Error):
    def __init__(self, position: Position, details:str = '') -> None:
        super().__init__(position, 'Validation Error', details)
        

class UnterminatedStringLiteralError(Error):
    def __init__(self, position: Position, details:str = '') -> None:
        super().__init__( position, 'Unterminated String Literal', details)
        
class RTError(Error):
    def __init__(self, position: Position, details:str, context: Context) -> None:
        super().__init__(position, 'Runtime Error', details)
        self.context = context
        
    @override
    def as_string(self) -> str:
        result = self.generate_traceback()
        result += f'{self.error_name}: {self.details}'
        result += '\n\n' + indicator_string(self.position.text, self.position)
        return result
    
    def generate_traceback(self) -> str:
        result = ''
        pos: Position | None = self.position
        context: Context | None = self.context
        
        while context:
            result = f' in {context.display_name}\n' + result
            pos = context.parent_entry_pos
            context = context.parent

        return 'Traceback (most recent call last):\n' + result



def console_supports_ansi() -> bool:
    """
    Heuristically checks if the console likely supports ANSI color codes.
    This is just a heuristic. For truly robust, cross-platform ANSI color handling, especially on older
    Windows versions, libraries like colorama or rich are excellent choices as they abstract away these detection
    and initialization complexities.
    todo research further.  This works when running from a terminal, but doesn't work when running from within IDEA.
    Returns:
        bool: True if ANSI colors are likely supported, False otherwise.
    """
    # Standard output must be a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    
    # Check for specific environments or TERM variable
    if os.name == 'posix':  # Linux, macOS, BSD, etc.
        term = os.environ.get('TERM', '').lower()
        # 'dumb' terminal definitely doesn't support color
        if term == 'dumb':
            return False
        # If TERM is set (and not 'dumb') or COLORTERM is present, likely supports color
        if term or 'COLORTERM' in os.environ:
            return True
        # Fallback for POSIX TTYs without clear TERM/COLORTERM might be False or True
        # depending on how optimistic you want to be. Let's be cautious.
        return False
    elif os.name == 'nt':  # Windows
        # Modern Windows Terminal sets WT_SESSION
        # ANSICON provides support for older cmd.exe
        # ConEmu sets CONEMUANSI
        if 'WT_SESSION' in os.environ or \
                'ANSICON' in os.environ or \
                os.environ.get('CONEMUANSI') == 'ON':
            return True
        # Terminals like Git Bash or Cygwin on Windows might set TERM
        term = os.environ.get('TERM', '').lower()
        if 'xterm' in term or 'cygwin' in term or 'ansi' in term:
            return True
        # For standard cmd.exe or PowerShell without these indicators,
        # ANSI support is not guaranteed without enabling VIRTUAL_TERMINAL_PROCESSING
        # or using a library like 'colorama'.
        return False  # Be conservative for unconfirmed Windows TTYs
    
    return False # Default for unknown OS or other cases
    
    
def indicator_string(text: str, position: Position, use_color: bool = True) -> str:
    """Return the str in `text` with a red-colored caret surrounding the error position in the text.
    The color is indicated via an ANSI color markup code which will display in red on supported consoles.
    No color markup is inserted if `use_color` is `False`."""
    color_prefix = color_suffix = ''
    #print(f"console_supports_ansi():{console_supports_ansi()}")
    if use_color: #  and console_supports_ansi():
        color_prefix = '\033[91m'
        color_suffix = '\033[0m'
    caret = f"{color_prefix}^{color_suffix}"
    result = f"{text[:position.start]}{caret}{text[position.start:position.end]}{caret}{text[position.end:]}"
    return result