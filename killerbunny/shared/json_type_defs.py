#  File: json_type_defs.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

from types import NoneType
from typing import TypeAlias, Union, Sequence, Mapping

# For use as type hints
JSON_PrimitiveType:  TypeAlias = Union[ str, int, float, bool, None ]  # RFC 8259, pg 3 calls these "primitive types"
JSON_ArrayType:      TypeAlias = Sequence[ 'JSON_ValueType' ]
JSON_ObjectType:     TypeAlias = Mapping[ str, 'JSON_ValueType']
JSON_StructuredType: TypeAlias = Union[ 'JSON_ArrayType', 'JSON_ObjectType']  #RFC 8259, pg 3 calls these "structured types"
JSON_ValueType:      TypeAlias = Union[ JSON_PrimitiveType, JSON_ArrayType, JSON_ObjectType]

# For use in isinstance(), e.g., if isinstance(foo, JSON_xxx_TYPES):
JSON_PRIMITIVE_TYPES   = ( str, int, float, bool, NoneType )
JSON_ARRAY_TYPES       = ( list, tuple, Sequence )
JSON_OBJECT_TYPES      = ( dict, Mapping)
JSON_STRUCTURED_TYPES  = ( dict, list, tuple, Mapping, Sequence )
JSON_VALUE_TYPES       = ( str, int, float, bool, NoneType, list, tuple, dict, Sequence, Mapping)






