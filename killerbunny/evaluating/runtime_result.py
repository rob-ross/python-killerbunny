#  File: runtime_result.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

from typing import Any


####################################################################
# RUNTIME RESULT
####################################################################
class RuntimeResult:
    def __init__(self) -> None:
        self.value = None
        self.error = None
    
    def register(self, result: Any) -> Any:
        if result.error: self.error = result.error
        return result.value
    
    def success(self, value: Any) -> 'RuntimeResult':
        self.value = value
        return self
    
    def failure(self, error: Any) -> 'RuntimeResult':
        self.error = error
        return self