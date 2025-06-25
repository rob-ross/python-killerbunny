#  File: lexer.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#

"""Scanner/tokenizer/lexer for JPath parser"""
import re
from typing import cast

from killerbunny.shared.errors import Error, IllegalCharError, UnterminatedStringLiteralError
from killerbunny.shared.position import Position
from killerbunny.lexing.tokens import Token, TokenType, STRING_DELIMETER_LEXEME_SET, \
    TWO_CHAR_LEXEMES_SET, TOKEN_LOOKUP_DICT, SINGLE_CHAR_LEXEMES_SET, JSON_KEYWORD_LEXEMES_SET
from killerbunny.shared.jpath_bnf import JPathBNFConstants as bnf


class JPathLexer:
    """Lexer for JPath parser"""
    
    def __init__(self, file_name: str, text: str) -> None:
        self.file_name: str = file_name
        self.text: str = text
        self.unparsed_text: str = text
        self.position: Position = Position( text, 0, 0)  # current scan position
        self.current_char: str | None = text[0] if len(text) > 0 else None
        self.tokens: list[Token] = []
    
    def advance(self, length_specifier: Token | TokenType | int) -> None:
        """Advance the position in the scanned text by the length of the `length_specifier` argument.
        """
        length:int
        if isinstance(length_specifier, Token):
            length = length_specifier.length
        elif isinstance(length_specifier, TokenType):
            length = len(length_specifier.lexeme)
        elif isinstance(length_specifier, int):
            length = length_specifier
        else:
            raise ValueError(f"Invalid token type: {type(length_specifier).__name__}")
            
        self.position.advance(length)
        self.unparsed_text = self.unparsed_text[length:]  # consume this token from the input stream
        self.current_char = self.unparsed_text[0] if len(self.unparsed_text) > 0 else None
    
    
    def advance_token(self,
                      token_type: TokenType,
                      value: str) -> Token:
        """Create and save the token to token_list, and advance lexer position by the length of the token."""
        token = self.make_token(token_type, value)
        self.tokens.append(token)
        self.advance(token)
        return token
        
        
    def peek_next_chars(self, number_chars:int = 1) -> str | None:
        """Return, without consuming, the first `number_chars` characters in the unparsed_text.
        Calling with number_chars=1 is the same as just referencing self.current_char."""
        endpoint = min(number_chars, len(self.unparsed_text))
        return self.unparsed_text[0:endpoint]
    
    
    def make_token(self, token_type: TokenType, value: str) -> Token:
        start = self.position.start
        end   = start + len(value)
        pos = Position(self.text, start, end)
        return Token(token_type, pos,  value)
    
    
    def match_string_literal(self) -> tuple[bool, Error | None]:
        """Match a string literal in between quotes. Handles empty string as well. Consumes quote characters and
        the string literal, if any.
        """
        opening_quote = self.current_char
        start_pos = self.position.start
        string: str = ''
        if self.current_char == bnf.SINGLE_QUOTE:
            self.advance(TokenType.SQUOTE)  # we don't create tokens for the quotes, they're part of the string literal
            match = re.match(bnf.STRING_LITERAL_SINGLE_QUOTEABLE, self.unparsed_text)
            if match:
                string = match.group("string_sq")
                #print(f"matched string={string}")
                #self.advance_token(TokenType.STRING, string)
                self.advance(len(string))
        elif self.current_char == bnf.DOUBLE_QUOTE:
            self.advance(TokenType.DQUOTE)
            match = re.match(bnf.STRING_LITERAL_DOUBLE_QUOTEABLE, self.unparsed_text)
            if match:
                string = match.group("string_dq")
                self.advance(len(string))
        else:
            return False, None

        # if no closing quote, return unterminated string literal error
        if self.current_char in STRING_DELIMETER_LEXEME_SET:
            value:str = self.current_char + string + self.current_char
            self.advance(1)  # if no quote or quote mismatch, there won't be another quote here. Since there is, we can advance
            end_pos = self.position.end
            string_pos = Position(self.position.text, start_pos, end_pos)
            string_token: Token = self.make_token(TokenType.STRING, value)
            string_token.position = string_pos
            self.tokens.append(string_token)  # we already advanced this string above
        else:
            if opening_quote == bnf.DOUBLE_QUOTE:
                details = "expected '\"'"
            else:
                details = 'expected "\'"'
                
            return False, UnterminatedStringLiteralError(self.position, details)
            
        return True, None
        
    
    def match_member_name_shorthand(self) -> bool:
        match = re.match(bnf.MEMBER_NAME_SHORTHAND, self.unparsed_text)
        if not match: return False
        
        string = match.group(0)
        if string in JSON_KEYWORD_LEXEMES_SET:
            # potentially a keyword. Parser can decide if it's a keyword or identifier in context
            token_type = TOKEN_LOOKUP_DICT[string]
            self.advance_token(token_type, string)
        else:
            self.advance_token(TokenType.IDENTIFIER, string)
        return True
    
    def match_slice_selector(self) -> bool:
        match = re.match(bnf.SLICE_SELECTOR, self.unparsed_text)
        if not match: return False
        self.advance_token(TokenType.SLICE, match.group(0))
        return True

    INT_RE:    re.Pattern[str] = re.compile(bnf.INT)
    NUMBER_RE: re.Pattern[str] = re.compile(bnf.NUMBER)
    
    def match_number(self) -> bool:
        num_str: str
        
        match = re.match(bnf.NUMBER, self.unparsed_text)
        if match is not None:
            num_str = match.group(0)
            token_type = TokenType.FLOAT
            if JPathLexer.INT_RE.fullmatch(num_str) is not None:
                token_type = TokenType.INT
            self.advance_token(token_type, num_str)
            return True
        
        return False  # couldn't parse a number
        
        
    def match_number_prev(self) -> bool:
        """ Interesting quirk in the grammar, -0 could parse successfully as a float number,
        because the frac_part and exp_part are optional for float.
        But -0 is not allowed in  IndexSelector, which is an int.
        This implementation will now treat -0 as an int, which will fail to parse and result in a lexer error. """
        num_str: str
        
        match = re.match(bnf.NUMBER, self.unparsed_text)
        if match is not None:
            num_str = match.group(0)
            if match.group("frac_part") is not None or match.group("exp_part") is not None:
                self.advance_token(TokenType.FLOAT, num_str)
                return True
            
        match = re.match(bnf.INT, self.unparsed_text)
        if match is not None:
            num_str = match.group(0)
            self.advance_token(TokenType.INT, num_str)
            return True
    

        return False

    
    def tokenize(self)  -> tuple[ list[Token], Error | None ]:
        """
        Scanning considerations:
        1. Check for multi-character operators first
        2. Then check for single-character operators
        3. Check for keywords before identifiers
        4. Check for literals (numbers, strings) based on their starting characters
        5. When several options are possible, look for the largest pattern first
        """
        while self.current_char is not None:
            match: re.Match[str] | None
            token_type:TokenType
            if self.current_char in bnf.BLANK_CHAR:  #  whitespace
                match = re.match(bnf.SPACES, self.unparsed_text)
                spaces = match.group(0)  # type: ignore
                token = self.make_token(TokenType.SPACE, spaces)
                #self.tokens.append(token)  # commentted out to consume all whitespace
                self.advance(token)  # advance without creating a token, i.e. eat the whitespace
                
            # multiple char tokens first. Need to peek at next character
            elif self.peek_next_chars(2) in TWO_CHAR_LEXEMES_SET:
                first_two_chars: str = cast(str, self.peek_next_chars(2))  # can't be None here because of elif above
                token_type = TOKEN_LOOKUP_DICT[ first_two_chars ]
                self.advance_token(token_type, token_type.lexeme)
                
            elif self.current_char in SINGLE_CHAR_LEXEMES_SET:
                token_type = TOKEN_LOOKUP_DICT[self.current_char]
                self.advance_token(token_type, token_type.lexeme)
                
            # Identifiers and keywords also handled here (member-name-shorthand, true, false, null, function names)
            #-----------------------------------------------------------------------------------------
            elif self.match_member_name_shorthand():
                continue  # match_member_name_shorthand() handled this
                
            # String literals
            elif self.current_char in STRING_DELIMETER_LEXEME_SET:
                matched, error = self.match_string_literal()
                if error is not None:
                    return self.tokens, error
                
            # slice selector
            elif self.current_char in bnf.SLICE_CHARS and self.match_slice_selector():
                # matched a slice selector
                continue
                
            # Numeric literal
            elif ( self.current_char in bnf.DIGITS or self.current_char == bnf.MINUS ) and self.match_number():
                continue  # match_number() handled the parsing of the number
                
            else:
                char = self.current_char
                position = Position(self.text, self.position.start, self.position.end + 1)
                self.advance_token(TokenType.UNKNOWN, char)
                return self.tokens, IllegalCharError(position, f"'{char}'")

        # to signal to the parser that a valid EOF was reached, as opposed to exiting early due to an error state
        self.tokens.append(self.make_token(TokenType.EOF, ''))
        return self.tokens, None
    