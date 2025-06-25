#  File: position.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#


####################################################################
# POSITION
####################################################################

class Position:
    """
    Holds a start and end index into a str, along with the str itself.
    """
    range_: range
    text: str
    @property
    def start(self) -> int:
        return self.range_.start
    
    @property
    def end(self) -> int:
        return self.range_.stop
    
    def __init__(self, text: str, start_index: int, end_index: int,
                 line_number: int = 0, column_number: int = 0, file_name:str = '', file_text: str = '' ) -> None:
        self.range_ = range(start_index, end_index)
        self.text = text
        
        # to support running queries from external files
        self.index = start_index  # this doesn't work well in this class, as Position is really a range, not a point.
        self.line_number = line_number
        self.column_number = column_number
        self.file_name = file_name
        self.file_text = file_text
        
    def __repr__(self) -> str:
        return f"Position(start={repr(self.range_.start)}, stop={repr(self.range_.stop)})"
    
    def __str__(self) -> str:
        return f"start={self.range_.start}, end={self.range_.stop}"
    
    
    def advance(self, count: int) -> 'Position':
        """Advance the position by the given count. This results in
        start += count and end += count. Returns this Position
        todo - have to refactor this class. As written, it's a fixed sliding window. Advancing moves the whole window,
        not a single position. This is confusing.
        """
        
        self.range_ = range(self.range_.start + count, self.range_.stop + count)
        return self
    
    def copy(self) -> 'Position':
        return Position(self.text, self.range_.start, self.range_.stop)
    

