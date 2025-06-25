#  File: context.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

from typing import Any

from killerbunny.shared.constants import ROOT_JSON_VALUE_KEY
from killerbunny.shared.json_type_defs import JSON_ValueType
from killerbunny.shared.position import Position


####################################################################
# CONTEXT
####################################################################

class Context:
    def __init__(self, display_name: str, parent: 'Context | None' = None, parent_entry_pos: Position | None = None) -> None:
        self._display_name:str = display_name
        self._parent: 'Context | None' = parent
        self._parent_entry_pos = parent_entry_pos
        self._symbol_table: SymbolTable = SymbolTable()
        
        
    @property
    def display_name(self) -> str:
        return self._display_name
    
    @property
    def parent(self) -> 'Context | None':
        return self._parent
    
    @property
    def parent_entry_pos(self) -> Position | None:
        return self._parent_entry_pos
        
    def get_symbol(self, symbol_name: str) -> Any:
        """Retrieve a symbol from this Context's symbol table. If the symbol is not found, and a parent Context exists,
        try to load the symbol from the parent Context. Returns None if the symbol is not found."""
        value = self._symbol_table.get(symbol_name)
        if value == None and self.parent is not None:
            return self.parent.get_symbol(symbol_name)
        return value
    
    def set_symbol(self, symbol_name: str, symbol: Any) -> None:
        """Store a symbol in this Context's symbol table."""
        self._symbol_table.set(symbol_name, symbol)


    @classmethod
    def root(cls, root_value: JSON_ValueType) -> 'Context':
        """Return a new Context with name 'root' and populate the symbol table with the argument as the root value"""
        context = Context("<root>")
        context.set_symbol(ROOT_JSON_VALUE_KEY, root_value)
        return context


####################################################################
# SYMBOL TABLE
####################################################################

class SymbolTable:
    def __init__(self) -> None:
        self._symbols: dict[str, Any] = {}
    
    def get(self, name: str) -> Any:
        return self._symbols.get(name, None)
    
    def set(self, name: str, value: Any) -> None:
        self._symbols[name] = value
    
    def remove(self, name: str) -> None:
        del self._symbols[name]
