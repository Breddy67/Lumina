# lumina/tokeniser.py
"""Tokeniser for the Lumina language."""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable
from enum import Enum, auto

from lumina_utils import is_alpha, is_digit, is_alphanum, explode


class TokenKind(Enum):
    """Token kinds."""
    LET = auto()
    IMPORT = auto()
    FROM = auto()
    CONFIG = auto()
    LOOP = auto()
    DRAW = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    IN = auto()
    ON = auto()
    EVERY = auto()
    FN = auto()
    RETURN = auto()
    NUMBER = auto()
    TIME = auto()
    STRING = auto()
    BOOL = auto()
    COLOR = auto()
    IDENT = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQ_EQ = auto()
    NOT_EQ = auto()
    LESS = auto()
    GREATER = auto()
    LESS_EQ = auto()
    GREATER_EQ = auto()
    AND = auto()
    NOT = auto()
    OR = auto()
    EQ = auto()
    PLUS_EQ = auto()
    MINUS_EQ = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()
    NEWLINE = auto()


@dataclass
class Pos:
    """Source position."""
    line: int
    col: int

    def __str__(self):
        return f"line {self.line}, col {self.col}"


@dataclass
class Token:
    """A token."""
    kind: TokenKind
    value: str
    text: str
    pos: Pos


def token_to_str(kind: TokenKind) -> str:
    """Convert token kind to string."""
    mapping = {
        TokenKind.LET: "LET",
        TokenKind.IMPORT: "IMPORT",
        TokenKind.FROM: "FROM",
        TokenKind.CONFIG: "CONFIG",
        TokenKind.LOOP: "LOOP",
        TokenKind.DRAW: "DRAW",
        TokenKind.IF: "IF",
        TokenKind.ELSE: "ELSE",
        TokenKind.FOR: "FOR",
        TokenKind.IN: "IN",
        TokenKind.ON: "ON",
        TokenKind.EVERY: "EVERY",
        TokenKind.FN: "FN",
        TokenKind.RETURN: "RETURN",
        TokenKind.NUMBER: "NUMBER",
        TokenKind.TIME: "TIME",
        TokenKind.STRING: "STRING",
        TokenKind.BOOL: "BOOL",
        TokenKind.COLOR: "COLOR",
        TokenKind.IDENT: "IDENT",
        TokenKind.PLUS: "PLUS",
        TokenKind.MINUS: "MINUS",
        TokenKind.STAR: "STAR",
        TokenKind.SLASH: "SLASH",
        TokenKind.EQ_EQ: "EQ_EQ",
        TokenKind.NOT_EQ: "NOT_EQ",
        TokenKind.LESS: "LESS",
        TokenKind.GREATER: "GREATER",
        TokenKind.LESS_EQ: "LESS_EQ",
        TokenKind.GREATER_EQ: "GREATER_EQ",
        TokenKind.AND: "AND",
        TokenKind.NOT: "NOT",
        TokenKind.OR: "OR",
        TokenKind.EQ: "EQ",
        TokenKind.PLUS_EQ: "PLUS_EQ",
        TokenKind.MINUS_EQ: "MINUS_EQ",
        TokenKind.LPAREN: "LPAREN",
        TokenKind.RPAREN: "RPAREN",
        TokenKind.LBRACE: "LBRACE",
        TokenKind.RBRACE: "RBRACE",
        TokenKind.LBRACKET: "LBRACKET",
        TokenKind.RBRACKET: "RBRACKET",
        TokenKind.COMMA: "COMMA",
        TokenKind.COLON: "COLON",
        TokenKind.DOT: "DOT",
        TokenKind.NEWLINE: "NEWLINE",
    }
    return mapping.get(kind, "UNKNOWN")


def print_token(t: Token) -> str:
    """Pretty print a token."""
    return f"{token_to_str(t.kind)}({t.text}) {t.value} [{t.pos}]"


def print_tokens(ts: List[Token]) -> str:
    """Pretty print a list of tokens."""
    return '\n'.join(print_token(t) for t in ts)


def take_while(chars: List[str], predicate: Callable[[str], bool]) -> Tuple[str, List[str]]:
    """Take characters while predicate holds."""
    result = []
    i = 0
    while i < len(chars) and predicate(chars[i]):
        result.append(chars[i])
        i += 1
    return ''.join(result), chars[i:]


def is_hex(c: str) -> bool:
    """Check if character is a hex digit."""
    return ('0' <= c <= '9') or ('a' <= c <= 'f') or ('A' <= c <= 'F')


def mk_token(kind: TokenKind, text: str, value: str, line: int, col: int) -> Token:
    """Create a token."""
    return Token(kind, value, text, Pos(line, col))


def tokenise_inner(chars: List[str], line: int, col: int) -> List[Token]:
    """Tokenise the input characters."""
    if not chars:
        return []

    c = chars[0]

    # Whitespace
    if c == ' ' or c == '\t' or c == '\r':
        return tokenise_inner(chars[1:], line, col + 1)

    # Newline
    if c == '\n':
        return [mk_token(TokenKind.NEWLINE, '\n', '', line, col)] + tokenise_inner(chars[1:], line + 1, 1)

    # Comments
    if len(chars) >= 2 and chars[0] == '/' and chars[1] == '/':
        skipped, rest = take_while(chars[2:], lambda ch: ch != '\n')
        return tokenise_inner(rest, line, col + 2 + len(skipped))

    # Multi-character operators
    if len(chars) >= 2:
        if chars[0] == '+' and chars[1] == '=':
            return [mk_token(TokenKind.PLUS_EQ, '+=', '', line, col)] + tokenise_inner(chars[2:], line, col + 2)
        if chars[0] == '-' and chars[1] == '=':
            return [mk_token(TokenKind.MINUS_EQ, '-=', '', line, col)] + tokenise_inner(chars[2:], line, col + 2)
        if chars[0] == '=' and chars[1] == '=':
            return [mk_token(TokenKind.EQ_EQ, '==', '', line, col)] + tokenise_inner(chars[2:], line, col + 2)
        if chars[0] == '<' and chars[1] == '=':
            return [mk_token(TokenKind.LESS_EQ, '<=', '', line, col)] + tokenise_inner(chars[2:], line, col + 2)
        if chars[0] == '>' and chars[1] == '=':
            return [mk_token(TokenKind.GREATER_EQ, '>=', '', line, col)] + tokenise_inner(chars[2:], line, col + 2)
        if chars[0] == '!' and chars[1] == '=':
            return [mk_token(TokenKind.NOT_EQ, '!=', '', line, col)] + tokenise_inner(chars[2:], line, col + 2)

    # Single-character operators
    if c == '=':
        return [mk_token(TokenKind.EQ, '=', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '+':
        return [mk_token(TokenKind.PLUS, '+', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '-':
        return [mk_token(TokenKind.MINUS, '-', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '*':
        return [mk_token(TokenKind.STAR, '*', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '/':
        return [mk_token(TokenKind.SLASH, '/', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '<':
        return [mk_token(TokenKind.LESS, '<', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '>':
        return [mk_token(TokenKind.GREATER, '>', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '!':
        return [mk_token(TokenKind.NOT, '!', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)

    # Braces and brackets
    if c == '{':
        return [mk_token(TokenKind.LBRACE, '{', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '}':
        return [mk_token(TokenKind.RBRACE, '}', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '(':
        return [mk_token(TokenKind.LPAREN, '(', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == ')':
        return [mk_token(TokenKind.RPAREN, ')', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '[':
        return [mk_token(TokenKind.LBRACKET, '[', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == ']':
        return [mk_token(TokenKind.RBRACKET, ']', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)

    # Punctuation
    if c == ',':
        return [mk_token(TokenKind.COMMA, ',', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == '.':
        return [mk_token(TokenKind.DOT, '.', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)
    if c == ':':
        return [mk_token(TokenKind.COLON, ':', '', line, col)] + tokenise_inner(chars[1:], line, col + 1)

    # Color literal: #[0-9a-fA-F]{6,8}
    if c == '#':
        hex_digits, rest = take_while(chars[1:], is_hex)
        if len(hex_digits) == 6:
            text = '#' + hex_digits
            return [mk_token(TokenKind.COLOR, text, text, line, col)] + tokenise_inner(rest, line, col + 7)
        elif len(hex_digits) == 8:
            text = '#' + hex_digits
            return [mk_token(TokenKind.COLOR, text, text, line, col)] + tokenise_inner(rest, line, col + 9)
        else:
            raise Exception(f"Tokenization error: Invalid color literal at {Pos(line, col)}")

    # String literal
    if c == '"':
        s, rest = take_while(chars[1:], lambda ch: ch != '"')
        if rest and rest[0] == '"':
            text = '"' + s + '"'
            return [mk_token(TokenKind.STRING, text, s, line, col)] + tokenise_inner(rest[1:], line, col + len(text))
        else:
            raise Exception(f"Tokenization error: Unterminated string at {Pos(line, col)}")

    # Identifiers and keywords
    if is_alpha(c):
        word_rest, rest = take_while(chars[1:], is_alphanum)
        word = c + word_rest
        keywords = {
            "let": TokenKind.LET,
            "import": TokenKind.IMPORT,
            "from": TokenKind.FROM,
            "config": TokenKind.CONFIG,
            "loop": TokenKind.LOOP,
            "draw": TokenKind.DRAW,
            "if": TokenKind.IF,
            "else": TokenKind.ELSE,
            "for": TokenKind.FOR,
            "in": TokenKind.IN,
            "on": TokenKind.ON,
            "every": TokenKind.EVERY,
            "fn": TokenKind.FN,
            "return": TokenKind.RETURN,
            "true": TokenKind.BOOL,
            "false": TokenKind.BOOL,
            "and": TokenKind.AND,
            "or": TokenKind.OR,
            "not": TokenKind.NOT,
        }
        if word in keywords:
            kind = keywords[word]
            value = word if kind == TokenKind.BOOL else ''
            return [mk_token(kind, word, value, line, col)] + tokenise_inner(rest, line, col + len(word))
        else:
            return [mk_token(TokenKind.IDENT, word, '', line, col)] + tokenise_inner(rest, line, col + len(word))

    # Number literals / time literals
    if is_digit(c):
        int_part, rest = take_while(chars[1:], is_digit)
        num = c + int_part

        if rest and rest[0] == '.' and len(rest) >= 2 and is_digit(rest[1]):
            d = rest[1]
            frac_rest, rest2 = take_while(rest[2:], is_digit)
            num = num + '.' + d + frac_rest

            if len(rest2) >= 2 and rest2[0] == 'm' and rest2[1] == 's':
                t = num + 'ms'
                return [mk_token(TokenKind.TIME, t, t, line, col)] + tokenise_inner(rest2[2:], line, col + len(t))
            elif len(rest2) >= 1 and rest2[0] == 's':
                t = num + 's'
                return [mk_token(TokenKind.TIME, t, t, line, col)] + tokenise_inner(rest2[1:], line, col + len(t))
            else:
                return [mk_token(TokenKind.NUMBER, num, num, line, col)] + tokenise_inner(rest2, line, col + len(num))

        if len(rest) >= 2 and rest[0] == 'm' and rest[1] == 's':
            t = num + 'ms'
            return [mk_token(TokenKind.TIME, t, t, line, col)] + tokenise_inner(rest[2:], line, col + len(t))
        elif len(rest) >= 1 and rest[0] == 's':
            t = num + 's'
            return [mk_token(TokenKind.TIME, t, t, line, col)] + tokenise_inner(rest[1:], line, col + len(t))
        else:
            return [mk_token(TokenKind.NUMBER, num, num, line, col)] + tokenise_inner(rest, line, col + len(num))

    raise Exception(f"Tokenization error: Unexpected character '{c}' at {Pos(line, col)}")


def tokenise(chars: List[str]) -> List[Token]:
    """Tokenise the input."""
    return tokenise_inner(chars, 1, 1)