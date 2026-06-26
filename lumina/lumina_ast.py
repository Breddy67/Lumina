"""Abstract Syntax Tree definitions for Lumina."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import List, Optional, Union, Tuple, Any


# Type expressions
@dataclass
class TPrim:
    """Primitive type."""
    name: str  # "Num", "Str", "Bool", "ColorLiteral", "Vec2", "Vec3"


@dataclass
class TArray:
    """Array type."""
    element: TypeExpr


@dataclass
class TTuple:
    """Tuple type."""
    elements: List[TypeExpr]


TypeExpr = Union[TPrim, TArray, TTuple]


# Binary operators
class BinOp:
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    EQ = "eq"
    NOT_EQ = "not_eq"
    LT = "lt"
    GT = "gt"
    LTEQ = "lt_eq"
    GTEQ = "gt_eq"
    AND = "and"
    OR = "or"


# Unary operators
class UnOp:
    NEG = "neg"
    NOT = "not"


# Call arguments
@dataclass
class PosArg:
    """Positional argument."""
    expr: Expr


@dataclass
class NameArg:
    """Named argument."""
    name: str
    expr: Expr


CallArg = Union[PosArg, NameArg]


# Access suffixes
@dataclass
class Field:
    """Field access suffix."""
    name: str


@dataclass
class Index:
    """Index access suffix."""
    expr: Expr


AccessSuffix = Union[Field, Index]


# Expressions
@dataclass
class Num:
    """Numeric literal."""
    value: float


@dataclass
class Str:
    """String literal."""
    value: str


@dataclass
class Bool:
    """Boolean literal."""
    value: bool


@dataclass
class ColorLiteral:
    """Color literal."""
    value: str  # Hex string like "#ff0000"


@dataclass
class Time:
    """Time literal."""
    value: float
    unit: str  # "s", "ms", "m"


@dataclass
class Ident:
    """Identifier."""
    name: str


@dataclass
class Tuple:
    """Tuple expression."""
    first: Expr
    second: Expr
    rest: List[Expr]


@dataclass
class Array:
    """Array expression."""
    elements: List[Expr]


@dataclass
class Binop:
    """Binary operation."""
    op: str
    left: Expr
    right: Expr


@dataclass
class Unop:
    """Unary operation."""
    op: str
    expr: Expr


@dataclass
class Call:
    """Function call."""
    name: str
    args: List[CallArg]


@dataclass
class Struct:
    """Structure construction."""
    name: str
    fields: List[Tuple[str, Expr]]


@dataclass
class Access:
    """Member/index access."""
    base: Expr
    suffixes: List[AccessSuffix]


# Expression types - use a simple class hierarchy approach
# Expr is a base class for all expression types
Expr = Any  # Type alias for any expression


# Assignment operators
class AssignOp:
    SET = "set"
    PLUS_SET = "plus_set"
    MINUS_SET = "minus_set"


# Accessor
@dataclass
class Accessor:
    """Base name with access suffixes."""
    name: str
    suffixes: List[AccessSuffix]


# Statements
@dataclass
class Let:
    """Let binding."""
    name: str
    type_annotation: Optional[TypeExpr]
    expr: Expr


@dataclass
class Return:
    """Return statement."""
    expr: Optional[Expr]


@dataclass
class Draw:
    """Draw statement."""
    expr: Expr


@dataclass
class If:
    """If statement."""
    cond: Expr
    then_body: List[Stmt]
    else_body: Optional[List[Stmt]]


@dataclass
class For:
    """For loop."""
    var: str
    iterable: Expr
    body: List[Stmt]


@dataclass
class Assign:
    """Assignment statement."""
    accessor: Accessor
    op: str
    expr: Expr


@dataclass
class ExprStmt:
    """Expression statement."""
    expr: Expr


Stmt = Union[Let, Return, Draw, If, For, Assign, ExprStmt]


# Top-level declarations
@dataclass
class FnDecl:
    """Function declaration."""
    name: str
    params: List[Tuple[str, Optional[TypeExpr]]]
    body: List[Stmt]


@dataclass
class EventBlock:
    """Event block."""
    trigger: Expr
    body: List[Stmt]


@dataclass
class TimeBlock:
    """Time block."""
    interval: Expr
    body: List[Stmt]


@dataclass
class LoopBlock:
    """Loop block."""
    body: List[Stmt]


TopLevel = Union[Stmt, FnDecl, EventBlock, TimeBlock, LoopBlock]


# Imports
@dataclass
class Import:
    """Import declaration."""
    name: str
    from_path: str


# Program
@dataclass
class Program:
    """Complete program."""
    imports: List[Import]
    config: List[Tuple[str, Expr]]
    items: List[TopLevel]


# Pretty printing functions
def pp_binop(op: str) -> str:
    """Pretty print binary operator."""
    mapping = {
        BinOp.ADD: "+", BinOp.SUB: "-", BinOp.MUL: "*", BinOp.DIV: "/",
        BinOp.EQ: "==", BinOp.NOT_EQ: "!=", BinOp.LT: "<", BinOp.GT: ">",
        BinOp.LTEQ: "<=", BinOp.GTEQ: ">=", BinOp.AND: "&&", BinOp.OR: "||",
    }
    return mapping.get(op, op)


def pp_unop(op: str) -> str:
    """Pretty print unary operator."""
    mapping = {UnOp.NEG: "-", UnOp.NOT: "!"}
    return mapping.get(op, op)


def pp_assign_op(op: str) -> str:
    """Pretty print assignment operator."""
    mapping = {
        AssignOp.SET: "=", AssignOp.PLUS_SET: "+=", AssignOp.MINUS_SET: "-="
    }
    return mapping.get(op, op)


def pp_type_expr(te: TypeExpr) -> str:
    """Pretty print type expression."""
    if isinstance(te, TPrim):
        return te.name
    elif isinstance(te, TArray):
        return f"[{pp_type_expr(te.element)}]"
    elif isinstance(te, TTuple):
        return f"({', '.join(pp_type_expr(e) for e in te.elements)})"
    return "unknown"


def pp_expr(e: Expr, indent: int = 0) -> str:
    """Pretty print expression."""
    if isinstance(e, Num):
        return str(int(e.value)) if e.value.is_integer() else str(e.value)
    elif isinstance(e, Str):
        return f'"{e.value}"'
    elif isinstance(e, Bool):
        return "true" if e.value else "false"
    elif isinstance(e, ColorLiteral):
        return e.value
    elif isinstance(e, Time):
        return f"{e.value}{e.unit}"
    elif isinstance(e, Ident):
        return e.name
    elif isinstance(e, Tuple):
        parts = [pp_expr(e.first), pp_expr(e.second)] + [pp_expr(x) for x in e.rest]
        return f"({', '.join(parts)})"
    elif isinstance(e, Array):
        return f"[{', '.join(pp_expr(x) for x in e.elements)}]"
    elif isinstance(e, Binop):
        return f"({pp_expr(e.left)} {pp_binop(e.op)} {pp_expr(e.right)})"
    elif isinstance(e, Unop):
        return f"({pp_unop(e.op)}{pp_expr(e.expr)})"
    elif isinstance(e, Call):
        args = []
        for arg in e.args:
            if isinstance(arg, PosArg):
                args.append(pp_expr(arg.expr))
            else:
                args.append(f"{arg.name}: {pp_expr(arg.expr)}")
        return f"{e.name}({', '.join(args)})"
    elif isinstance(e, Struct):
        fields = [f"{k}: {pp_expr(v)}" for k, v in e.fields]
        return f"{e.name} {{ {', '.join(fields)} }}"
    elif isinstance(e, Access):
        suffix_str = []
        for s in e.suffixes:
            if isinstance(s, Field):
                suffix_str.append(f".{s.name}")
            else:
                suffix_str.append(f"[{pp_expr(s.expr)}]")
        return pp_expr(e.base) + ''.join(suffix_str)
    return "unknown"


def pp_stmt(s: Stmt, indent: int = 0) -> str:
    """Pretty print statement."""
    pad = "  " * indent
    if isinstance(s, Let):
        type_str = f": {pp_type_expr(s.type_annotation)}" if s.type_annotation else ""
        return f"{pad}let {s.name}{type_str} = {pp_expr(s.expr)}"
    elif isinstance(s, Return):
        return f"{pad}return {pp_expr(s.expr) if s.expr else ''}"
    elif isinstance(s, Draw):
        return f"{pad}draw {pp_expr(s.expr)}"
    elif isinstance(s, If):
        body = '\n'.join(pp_stmt(st, indent + 1) for st in s.then_body)
        if s.else_body:
            else_body = '\n'.join(pp_stmt(st, indent + 1) for st in s.else_body)
            return f"{pad}if ({pp_expr(s.cond)}) {{\n{body}\n{pad}}} else {{\n{else_body}\n{pad}}}"
        return f"{pad}if ({pp_expr(s.cond)}) {{\n{body}\n{pad}}}"
    elif isinstance(s, For):
        body = '\n'.join(pp_stmt(st, indent + 1) for st in s.body)
        return f"{pad}for {s.var} in {pp_expr(s.iterable)} {{\n{body}\n{pad}}}"
    elif isinstance(s, Assign):
        suffix_str = ''.join(f".{sf.name}" if isinstance(sf, Field) else f"[{pp_expr(sf.expr)}]" for sf in s.accessor.suffixes)
        return f"{pad}{s.accessor.name}{suffix_str} {pp_assign_op(s.op)} {pp_expr(s.expr)}"
    elif isinstance(s, ExprStmt):
        return f"{pad}{pp_expr(s.expr)}"
    return ""


def pp_top_level(t: TopLevel) -> str:
    """Pretty print top-level declaration."""
    if isinstance(t, FnDecl):
        params = []
        for p, te in t.params:
            params.append(f"{p}: {pp_type_expr(te)}" if te else p)
        body = '\n'.join(pp_stmt(st, 1) for st in t.body)
        return f"fn {t.name}({', '.join(params)}) {{\n{body}\n}}"
    elif isinstance(t, EventBlock):
        body = '\n'.join(pp_stmt(st, 1) for st in t.body)
        return f"on {pp_expr(t.trigger)} {{\n{body}\n}}"
    elif isinstance(t, TimeBlock):
        body = '\n'.join(pp_stmt(st, 1) for st in t.body)
        return f"every {pp_expr(t.interval)} {{\n{body}\n}}"
    elif isinstance(t, LoopBlock):
        body = '\n'.join(pp_stmt(st, 1) for st in t.body)
        return f"loop {{\n{body}\n}}"
    elif isinstance(t, Stmt):
        return pp_stmt(t)
    return ""


def pp_program(p: Program) -> str:
    """Pretty print a program."""
    imports = [f'import {imp.name} from "{imp.from_path}"' for imp in p.imports]
    config = []
    if p.config:
        config = ["config {"] + [f"  {k}: {pp_expr(v)}" for k, v in p.config] + ["}"]
    items = [pp_top_level(item) for item in p.items]
    return '\n\n'.join([s for s in imports + config + items if s])