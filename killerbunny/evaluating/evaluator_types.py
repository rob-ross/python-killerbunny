import re

from killerbunny.shared.jpath_bnf import JPathNormalizedPathBNF

#  File: evaluator_types.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
import abc
from typing import Self

from killerbunny.shared.context import Context
from killerbunny.shared.json_type_defs import JSON_ValueType
from killerbunny.shared.position import Position
from killerbunny.parsing.helper import escape_string_content


class EvaluatorValue:
    """ Base class for Evaluator value objects like numbers, strings, booleans, node lists, etc. """
    
    _position : Position | None
    _context  : Context  | None
    
    def __init__(self) -> None:
        self.set_pos()
        self.set_context()
    
    @property
    def position(self) -> Position | None:
        return self._position
    
    @property
    def context(self) -> Context | None:
        return self._context
    
    def set_pos(self, position: Position | None = None) -> Self:
        self._position = position
        return self
    
    def set_context(self, context: Context | None = None) -> Self:
        self._context = context
        return self
    
    @property
    @abc.abstractmethod
    def value(self) -> JSON_ValueType:
        ...


NORMALIZED_PATH_RE = re.compile(JPathNormalizedPathBNF.NORMALIZED_PATH)


class NormalizedJPath:
    """Holds a noralized JSONPath as a str. Contains methods for obtaining a list of path segments for the jpath as
    well as constructing an instance from a list of path segments."""
    def __init__(self, jpath_str: str) -> None:
        super().__init__()
        self._jpath_str = self.normalize_path(jpath_str)
        
    @property
    def jpath_str(self) -> str:
        """ todo - does this *really* need to be more complicated than a Python str? I don't see any reason YET."""
        return self._jpath_str
    
    @staticmethod
    def normalize_path(jpath_str: str) -> str:
        """Given a well-formed and valid JSON Path str, return a normalized form of the jpath. If the jpath cannot be
        normalized or is not well-formed and valid, raise a ValueError."""
        if not jpath_str:
            raise ValueError("jpath_str cannot be None nor empty")
        escaped_path = escape_string_content(jpath_str)
        match = NORMALIZED_PATH_RE.match(escaped_path)
        if match:
            return escaped_path
        else: raise ValueError(f"jpath_str: '{jpath_str}' is not in normal format.")
        # todo : to verify that a jpath is well-formed we actualy need to run it through the lexer and parser!
        # this produces an AST, however. So we would need a special evalute method in the Evaluator to construct the
        # jpath and verify it only contains legitimate jpath syntax.
        # for now, we will assume the paths in the initializer are correct
    
    def __repr__(self) -> str:
        return f"NormalizedJPath(jpath_str={repr(self.jpath_str)})"
    
    def __str__(self) -> str:
        return self._jpath_str
