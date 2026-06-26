# lumina/codegen.py
"""Code generation for the Lumina language."""

from typing import List, Optional, Tuple, Dict, Any, Set
from dataclasses import dataclass
import math
import re

import lumina_ast as ast
import lumina_types
import predefined
from lumina_types import Typ, TNum, TBool, TStr, TColor, TTime, TTuple, TArray, TStruct, TFn, TVoid, TAny, TShape, pp_typ
from errors import raise_codegen_error


class CType:
    FLOAT = "float"
    BOOL = "bool"
    STRING = "const char*"
    VECTOR2 = "Vector2"
    VECTOR3 = "Vector3"
    COLOR = "Color"
    VOID = "void"


class Mode:
    INTERACTIVE = "interactive"
    RENDER = "render"


@dataclass
class Config:
    width: int = 800
    height: int = 600
    fps: int = 60
    duration: Optional[int] = None
    mode: str = Mode.INTERACTIVE
    bg_color: Optional[Tuple[int, int, int, int]] = None
    title: str = "Lumen"


@dataclass
class Env:
    bindings: List[Tuple[str, str]] = None  # name -> ctype

    def __post_init__(self):
        if self.bindings is None:
            self.bindings = []

    def lookup(self, name: str) -> Optional[str]:
        for n, t in reversed(self.bindings):
            if n == name:
                return t
        return None

    def add(self, name: str, ctype: str) -> 'Env':
        return Env(self.bindings + [(name, ctype)])


# Function return types
fn_returns: Dict[str, str] = {}


def ctype_of_typ(t: Typ) -> str:
    """Convert a type to a C type."""
    if isinstance(t, TNum) or isinstance(t, TTime):
        return CType.FLOAT
    elif isinstance(t, TBool):
        return CType.BOOL
    elif isinstance(t, TStr):
        return CType.STRING
    elif isinstance(t, TColor):
        return CType.COLOR
    elif isinstance(t, TTuple):
        elems = t.elements
        if len(elems) == 2:
            return CType.VECTOR2
        elif len(elems) == 3:
            return CType.VECTOR3
        else:
            return CType.FLOAT
    elif isinstance(t, TArray):
        et = ctype_of_typ(t.element_type)
        if et == CType.VECTOR2:
            return "vector_v2*"
        elif et == CType.VECTOR3:
            return "vector_v3*"
        else:
            return "vector*"
    elif isinstance(t, TStruct):
        return CType.VOID
    elif isinstance(t, TFn):
        return CType.VOID
    elif isinstance(t, TShape):
        return CType.VOID
    elif isinstance(t, TAny):
        return CType.VOID
    elif isinstance(t, TVoid):
        return CType.VOID
    return CType.FLOAT


def lookup_env(env: Env, name: str) -> Optional[str]:
    """Look up a name in the environment."""
    return env.lookup(name)


def parse_hex_color(s: str) -> Optional[Tuple[int, int, int, int]]:
    """Parse a hex color string."""
    if s.startswith('#'):
        s = s[1:]
    try:
        if len(s) == 6:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            return (r, g, b, 255)
        elif len(s) == 8:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            a = int(s[6:8], 16)
            return (r, g, b, a)
    except ValueError:
        pass
    return None


def extract_config(items: List[Tuple[str, ast.Expr]]) -> Config:
    """Extract configuration from config items."""
    cfg = Config()

    for key, value in items:
        if key == "width" and isinstance(value, ast.Num):
            cfg.width = int(value.value)
        elif key == "height" and isinstance(value, ast.Num):
            cfg.height = int(value.value)
        elif key == "fps" and isinstance(value, ast.Num):
            cfg.fps = int(value.value)
        elif key == "duration":
            if isinstance(value, ast.Num):
                cfg.duration = int(value.value)
                cfg.mode = Mode.RENDER
            elif isinstance(value, ast.Time):
                if value.unit == "s":
                    cfg.duration = int(value.value)
                elif value.unit == "ms":
                    cfg.duration = int(value.value / 1000.0)
                cfg.mode = Mode.RENDER
        elif key == "mode":
            if isinstance(value, ast.Ident):
                if value.name == "interactive":
                    cfg.mode = Mode.INTERACTIVE
                elif value.name == "render":
                    cfg.mode = Mode.RENDER
        elif key == "title" and isinstance(value, ast.Str):
            cfg.title = value.value
        elif key == "background" and isinstance(value, ast.ColorLiteral):
            rgba = parse_hex_color(value.value)
            if rgba:
                cfg.bg_color = rgba

    return cfg


def is_render_mode(prog: ast.Program) -> bool:
    """Check if the program is in render mode."""
    cfg = extract_config(prog.config)
    return cfg.mode == Mode.RENDER


def color_literal(r: int, g: int, b: int, a: int) -> str:
    """Generate a color literal."""
    return f"(Color){{ {r}, {g}, {b}, {a} }}"


default_bg_color = (15, 15, 25, 255)
default_fg_color = (255, 255, 255, 255)


def emit_float(f: float) -> str:
    """Emit a float literal."""
    if f.is_integer():
        return f"{int(f)}.0f"
    return f"{f}f"


def magic_ident(mode: str, name: str) -> Optional[str]:
    """Get the C expression for a magic identifier."""
    if mode == Mode.INTERACTIVE:
        if name == "width":
            return "GetScreenWidth()"
        elif name == "height":
            return "GetScreenHeight()"
    else:
        if name == "width":
            return "WIDTH"
        elif name == "height":
            return "HEIGHT"

    return predefined.var_expr(name)


def gen_expr(env: Env, mode: str, expr: ast.Expr) -> str:
    """Generate C code for an expression."""
    if isinstance(expr, ast.Num):
        return emit_float(expr.value)
    elif isinstance(expr, ast.Str):
        return f'"{expr.value}"'
    elif isinstance(expr, ast.Bool):
        return "true" if expr.value else "false"
    elif isinstance(expr, ast.Time):
        if expr.unit == "s":
            return emit_float(expr.value)
        elif expr.unit == "ms":
            return emit_float(expr.value / 1000.0)
        elif expr.unit == "m":
            return emit_float(expr.value * 60.0)
        return emit_float(expr.value)
    elif isinstance(expr, ast.ColorLiteral):
        rgba = parse_hex_color(expr.value)
        if rgba:
            return color_literal(*rgba)
        return "(Color){ 255, 255, 255, 255 }"
    elif isinstance(expr, ast.Ident):
        magic = magic_ident(mode, expr.name)
        if magic is not None:
            return magic
        return expr.name
    elif isinstance(expr, ast.Tuple):
        if len(expr.rest) == 0:
            return f"(Vector2){{ {gen_expr(env, mode, expr.first)}, {gen_expr(env, mode, expr.second)} }}"
        elif len(expr.rest) == 1:
            return f"(Vector3){{ {gen_expr(env, mode, expr.first)}, {gen_expr(env, mode, expr.second)}, {gen_expr(env, mode, expr.rest[0])} }}"
        else:
            all_exprs = [expr.first, expr.second] + expr.rest
            parts = [gen_expr(env, mode, e) for e in all_exprs]
            return "{ " + ", ".join(parts) + " }"
    elif isinstance(expr, ast.Array):
        parts = [gen_expr(env, mode, e) for e in expr.elements]
        return "{ " + ", ".join(parts) + " }"
    elif isinstance(expr, ast.Binop):
        return gen_binop(env, mode, expr.op, expr.left, expr.right)
    elif isinstance(expr, ast.Unop):
        if expr.op == ast.UnOp.NEG:
            return f"(-{gen_expr(env, mode, expr.expr)})"
        elif expr.op == ast.UnOp.NOT:
            return f"(!{gen_expr(env, mode, expr.expr)})"
    elif isinstance(expr, ast.Call):
        return gen_call(env, mode, expr.name, expr.args)
    elif isinstance(expr, ast.Struct):
        fields = [gen_expr(env, mode, v) for _, v in expr.fields]
        if expr.name == "Vec2":
            return f"(Vector2){{ {', '.join(fields)} }}"
        elif expr.name == "Vec3":
            return f"(Vector3){{ {', '.join(fields)} }}"
        elif expr.name == "Color":
            return f"(Color){{ {', '.join(fields)} }}"
        else:
            return f"({expr.name}){{ {', '.join(fields)} }}"
    elif isinstance(expr, ast.Access):
        return gen_access(env, mode, expr)

    return ""


def gen_access(env: Env, mode: str, expr: ast.Access) -> str:
    """Generate C code for an access expression."""
    if not expr.suffixes:
        return gen_expr(env, mode, expr.base)

    # Build the base expression
    base_expr = expr
    suffixes = expr.suffixes

    # For simple access, we need to determine the type of the base
    # We'll use a simplified approach: just generate the access chain
    base_str = gen_expr(env, mode, expr.base)

    # Generate suffixes
    result = base_str
    for suffix in suffixes:
        if isinstance(suffix, ast.Field):
            result += f".{suffix.name}"
        elif isinstance(suffix, ast.Index):
            result += f"[{gen_expr(env, mode, suffix.expr)}]"

    return result


def gen_suffix(env: Env, mode: str, lhs_type: Optional[str], suffix: ast.AccessSuffix) -> str:
    """Generate C code for an access suffix."""
    if suffix is None:
        return ""

    if isinstance(suffix, ast.Field):
        return f".{suffix.name}"
    elif isinstance(suffix, ast.Index):
        return f"[{gen_expr(env, mode, suffix.expr)}]"
    return ""


def gen_binop(env: Env, mode: str, op: str, left: ast.Expr, right: ast.Expr) -> str:
    """Generate C code for a binary operation."""
    sl = gen_expr(env, mode, left)
    sr = gen_expr(env, mode, right)

    # Vector arithmetic via raymath
    # We'll use a simplified approach - check if operands are tuples
    # For now, just generate the basic operation
    op_map = {
        ast.BinOp.ADD: "+",
        ast.BinOp.SUB: "-",
        ast.BinOp.MUL: "*",
        ast.BinOp.DIV: "/",
        ast.BinOp.EQ: "==",
        ast.BinOp.NOT_EQ: "!=",
        ast.BinOp.LT: "<",
        ast.BinOp.GT: ">",
        ast.BinOp.LTEQ: "<=",
        ast.BinOp.GTEQ: ">=",
        ast.BinOp.AND: "&&",
        ast.BinOp.OR: "||",
    }

    return f"({sl} {op_map.get(op, '+')} {sr})"


def gen_call(env: Env, mode: str, name: str, args: List[ast.CallArg]) -> str:
    """Generate C code for a function call."""
    pos_args = []
    named_args = {}

    for arg in args:
        if isinstance(arg, ast.PosArg):
            pos_args.append(gen_expr(env, mode, arg.expr))
        else:
            named_args[arg.name] = gen_expr(env, mode, arg.expr)

    # Check if it's a predefined function
    pred = predefined.find(name)
    if pred and pred.impl:
        return pred.impl(pos_args)

    # Default: generate a function call
    all_args = pos_args
    for name, value in named_args.items():
        all_args.append(value)

    return f"{name}({', '.join(all_args)})"


def resolve_color(env: Env, mode: str, args: List[ast.CallArg], default_color: Tuple[int, int, int, int]) -> str:
    """Resolve a color from arguments."""
    for arg in args:
        if isinstance(arg, ast.NameArg) and arg.name == "color":
            return gen_expr(env, mode, arg.expr)
    return color_literal(*default_color)


def pos_int(env: Env, mode: str, e: ast.Expr) -> str:
    """Generate code for a position as ints."""
    s = gen_expr(env, mode, e)
    return f"(int)(({s}).x), (int)(({s}).y)"


def gen_draw_call(env: Env, mode: str, expr: ast.Expr) -> str:
    """Generate C code for a draw call."""
    if not isinstance(expr, ast.Call):
        return f"/* draw */ {gen_expr(env, mode, expr)};"

    name = expr.name
    args = expr.args

    # Helper to get a positional argument
    def get_arg(idx: int) -> ast.Expr:
        pos_args = [a for a in args if isinstance(a, ast.PosArg)]
        if idx < len(pos_args):
            return pos_args[idx].expr
        return ast.Num(0.0)

    if name == "Circle":
        pos = gen_expr(env, mode, get_arg(0))
        r = gen_expr(env, mode, get_arg(1))
        c = resolve_color(env, mode, args, default_fg_color)
        return f"DrawCircle((int)(({pos}).x), (int)(({pos}).y), {r}, {c});"

    elif name == "Rect":
        pos = gen_expr(env, mode, get_arg(0))
        w = gen_expr(env, mode, get_arg(1))
        h = gen_expr(env, mode, get_arg(2))
        c = resolve_color(env, mode, args, default_fg_color)
        return f"DrawRectangle((int)(({pos}).x), (int)(({pos}).y), (int){w}, (int){h}, {c});"

    elif name == "RectOutline":
        pos = gen_expr(env, mode, get_arg(0))
        w = gen_expr(env, mode, get_arg(1))
        h = gen_expr(env, mode, get_arg(2))
        c = resolve_color(env, mode, args, default_fg_color)
        return f"DrawRectangleLines((int)(({pos}).x), (int)(({pos}).y), (int){w}, (int){h}, {c});"

    elif name == "CircleOutline":
        pos = gen_expr(env, mode, get_arg(0))
        r = gen_expr(env, mode, get_arg(1))
        c = resolve_color(env, mode, args, default_fg_color)
        return f"DrawCircleLines((int)(({pos}).x), (int)(({pos}).y), {r}, {c});"

    elif name == "Line":
        a = gen_expr(env, mode, get_arg(0))
        b = gen_expr(env, mode, get_arg(1))
        c = resolve_color(env, mode, args, default_fg_color)
        return f"DrawLineV({a}, {b}, {c});"

    elif name == "Triangle":
        a = gen_expr(env, mode, get_arg(0))
        b = gen_expr(env, mode, get_arg(1))
        c_pt = gen_expr(env, mode, get_arg(2))
        col = resolve_color(env, mode, args, default_fg_color)
        return f"DrawTriangle({a}, {b}, {c_pt}, {col});"

    elif name == "Pixel":
        pos = gen_expr(env, mode, get_arg(0))
        c = resolve_color(env, mode, args, default_fg_color)
        return f"DrawPixel((int)(({pos}).x), (int)(({pos}).y), {c});"

    elif name == "Text":
        s = gen_expr(env, mode, get_arg(0))
        pos = gen_expr(env, mode, get_arg(1))

        # Check for size argument
        size = "20.0f"
        for arg in args:
            if isinstance(arg, ast.NameArg) and arg.name == "size":
                size = gen_expr(env, mode, arg.expr)
                break
        # Also check positional argument 2
        pos_args = [a for a in args if isinstance(a, ast.PosArg)]
        if len(pos_args) >= 3:
            size = gen_expr(env, mode, pos_args[2].expr)

        c = resolve_color(env, mode, args, default_fg_color)
        return f"DrawText({s}, (int)(({pos}).x), (int)(({pos}).y), (int)({size}), {c});"

    elif name == "Arc":
        pos = gen_expr(env, mode, get_arg(0))
        r = gen_expr(env, mode, get_arg(1))
        sa = gen_expr(env, mode, get_arg(2))
        ea = gen_expr(env, mode, get_arg(3))
        c = resolve_color(env, mode, args, default_fg_color)
        return f"DrawCircleSector({pos}, {r}, {sa}, {ea}, 32, {c});"

    else:
        return f"/* draw */ {gen_expr(env, mode, expr)};"


def indent(n: int) -> str:
    """Generate an indentation string."""
    return " " * (n * 4)


def type_expr_to_typ(te: ast.TypeExpr) -> Typ:
    """Convert a type expression to a type."""
    if isinstance(te, ast.TPrim):
        mapping = {
            "Num": TNum(),
            "Str": TStr(),
            "Bool": TBool(),
            "Color": TColor(),
            "Vec2": TTuple([TNum(), TNum()]),
            "Vec3": TTuple([TNum(), TNum(), TNum()]),
        }
        return mapping.get(te.name, TAny())
    elif isinstance(te, ast.TArray):
        return TArray(type_expr_to_typ(te.element))
    elif isinstance(te, ast.TTuple):
        return TTuple([type_expr_to_typ(e) for e in te.elements])
    return TAny()


def gen_stmt(env: Env, mode: str, depth: int, stmt: ast.Stmt) -> Tuple[Env, List[str]]:
    """Generate C code for a statement."""
    pad = indent(depth)

    if isinstance(stmt, ast.Let):
        # Determine the type from the expression
        if isinstance(stmt.expr, ast.Tuple):
            if len(stmt.expr.rest) == 0:
                t = CType.VECTOR2
            elif len(stmt.expr.rest) == 1:
                t = CType.VECTOR3
            else:
                t = CType.FLOAT
        elif isinstance(stmt.expr, ast.Array):
            t = "vector*"  # Default array type
        elif isinstance(stmt.expr, ast.Num):
            t = CType.FLOAT
        elif isinstance(stmt.expr, ast.Str):
            t = CType.STRING
        elif isinstance(stmt.expr, ast.Bool):
            t = CType.BOOL
        elif isinstance(stmt.expr, ast.ColorLiteral):
            t = CType.COLOR
        else:
            t = CType.FLOAT  # Default

        new_env = env.add(stmt.name, t)

        if isinstance(stmt.expr, ast.Array):
            # Array literal
            elems = stmt.expr.elements
            n = max(4, len(elems))
            struct_name = "vector*"
            create_fn = "create"
            push_fn = "push"
            # Check if it's a vector array
            if elems and isinstance(elems[0], ast.Tuple):
                if len(elems[0].rest) == 0:
                    struct_name = "vector_v2*"
                    create_fn = "create_v2"
                    push_fn = "push_v2"
                elif len(elems[0].rest) == 1:
                    struct_name = "vector_v3*"
                    create_fn = "create_v3"
                    push_fn = "push_v3"

            lines = [f"{pad}{struct_name} {stmt.name} = {create_fn}({n});"]
            for elem in elems:
                lines.append(f"{pad}{push_fn}({stmt.name}, {gen_expr(env, mode, elem)});")
            return new_env, lines

        else:
            ve = gen_expr(env, mode, stmt.expr)
            if t == CType.VECTOR2:
                a = gen_expr(env, mode, stmt.expr.first)
                b = gen_expr(env, mode, stmt.expr.second)
                return new_env, [f"{pad}Vector2 {stmt.name} = {{ {a}, {b} }};"]
            elif t == CType.VECTOR3:
                a = gen_expr(env, mode, stmt.expr.first)
                b = gen_expr(env, mode, stmt.expr.second)
                c = gen_expr(env, mode, stmt.expr.rest[0]) if stmt.expr.rest else "0.0f"
                return new_env, [f"{pad}Vector3 {stmt.name} = {{ {a}, {b}, {c} }};"]
            else:
                return new_env, [f"{pad}{t} {stmt.name} = {ve};"]
            
    elif isinstance(stmt, ast.Return):
        if stmt.expr:
            return env, [f"{pad}return {gen_expr(env, mode, stmt.expr)};"]
        else:
            return env, [f"{pad}return;"]

    elif isinstance(stmt, ast.ExprStmt):
        s = gen_expr(env, mode, stmt.expr)
        if s:
            return env, [f"{pad}{s};"]
        return env, []

    elif isinstance(stmt, ast.Assign):
        # Generate assignment
        lhs = stmt.accessor.name
        if stmt.accessor.suffixes:
            lhs += ''.join(gen_suffix(env, mode, None, s) for s in stmt.accessor.suffixes)

        op_map = {
            ast.AssignOp.SET: "=",
            ast.AssignOp.PLUS_SET: "+=",
            ast.AssignOp.MINUS_SET: "-=",
        }

        return env, [f"{pad}{lhs} {op_map.get(stmt.op, '=')} {gen_expr(env, mode, stmt.expr)};"]

    elif isinstance(stmt, ast.If):
        cond_s = gen_expr(env, mode, stmt.cond)
        open_lines = [f"{pad}if ({cond_s}) {{"]
        _, then_lines = gen_stmts(env, mode, depth + 1, stmt.then_body)

        if stmt.else_body:
            _, else_lines = gen_stmts(env, mode, depth + 1, stmt.else_body)
            close_lines = [f"{pad}}} else {{"] + else_lines + [f"{pad}}}"]
        else:
            close_lines = [f"{pad}}}"]

        return env, open_lines + then_lines + close_lines

    elif isinstance(stmt, ast.For):
        # For loop
        if isinstance(stmt.iterable, ast.Array):
            # Iterating over an array literal
            elems = stmt.iterable.elements
            if elems:
                elem_typ = "float"  # Default
                # Try to infer element type
                # For simplicity, use float
                elem_ct = "float"
                struct_name = "vector*"
                create_fn = "create"
                push_fn = "push"
            else:
                elem_ct = "float"
                struct_name = "vector*"
                create_fn = "create"
                push_fn = "push"

            inner_env = env.add(stmt.var, elem_ct)
            _, body_lines = gen_stmts(inner_env, mode, depth + 1, stmt.body)

            n = max(4, len(elems))
            tmp = "_for_arr"
            pre = [
                f"{pad}{{ {struct_name} {tmp} = {create_fn}({n});"
            ]
            for elem in elems:
                pre.append(f"{pad}  {push_fn}({tmp}, {gen_expr(env, mode, elem)});")

            loop_h = f"{pad}  for (int _i = 0; _i < {tmp}->size; _i++) {{"
            elem_line = f"{indent(depth + 2)}{elem_ct} {stmt.var} = {tmp}->data[_i];"

            return env, pre + [loop_h, elem_line] + body_lines + [f"{pad}  }}", f"{pad}}}"]
        else:
            iter_s = gen_expr(env, mode, stmt.iterable)
            inner_env = env.add(stmt.var, "float")
            _, body_lines = gen_stmts(inner_env, mode, depth + 1, stmt.body)

            # Check if it's a range call
            if isinstance(stmt.iterable, ast.Call) and stmt.iterable.name == "range":
                args = stmt.iterable.args
                pos_args = [a for a in args if isinstance(a, ast.PosArg)]
                if len(pos_args) >= 1:
                    lo = "0"
                    hi = gen_expr(env, mode, pos_args[0].expr)
                    step = "1"
                    if len(pos_args) >= 2:
                        lo = gen_expr(env, mode, pos_args[0].expr)
                        hi = gen_expr(env, mode, pos_args[1].expr)
                    if len(pos_args) >= 3:
                        step = gen_expr(env, mode, pos_args[2].expr)

                    loop_h = f"{pad}for (float {stmt.var} = {lo}; {stmt.var} < {hi}; {stmt.var} += {step}) {{"
                    return env, [loop_h] + body_lines + [f"{pad}}}"]
                elif len(pos_args) == 1:
                    hi = gen_expr(env, mode, pos_args[0].expr)
                    loop_h = f"{pad}for (float {stmt.var} = 0; {stmt.var} < {hi}; {stmt.var}++) {{"
                    return env, [loop_h] + body_lines + [f"{pad}}}"]

            loop_h = f"{pad}for (float {stmt.var} = 0; {stmt.var} < {iter_s}; {stmt.var}++) {{"
            return env, [loop_h] + body_lines + [f"{pad}}}"]

    elif isinstance(stmt, ast.Draw):
        return env, [f"{pad}{gen_draw_call(env, mode, stmt.expr)}"]

    return env, []


def gen_stmts(env: Env, mode: str, depth: int, stmts: List[ast.Stmt]) -> Tuple[Env, List[str]]:
    """Generate C code for a list of statements."""
    current_env = env
    lines = []
    for stmt in stmts:
        new_env, new_lines = gen_stmt(current_env, mode, depth, stmt)
        current_env = new_env
        lines.extend(new_lines)
    return current_env, lines


def ctype_str(t: str) -> str:
    """Convert a C type string to a printable form."""
    return t


def is_draw_stmt(stmt: ast.Stmt) -> bool:
    """Check if a statement is a draw statement."""
    if isinstance(stmt, ast.Draw):
        return True
    if isinstance(stmt, ast.ExprStmt):
        if isinstance(stmt.expr, ast.Call) and stmt.expr.name == "clear":
            return True
    return False


def stmt_contains_draw(stmt: ast.Stmt) -> bool:
    """Check if a statement contains a draw."""
    if isinstance(stmt, ast.Draw):
        return True
    if isinstance(stmt, ast.ExprStmt):
        if isinstance(stmt.expr, ast.Call) and stmt.expr.name == "clear":
            return True
    if isinstance(stmt, ast.If):
        if any(stmt_contains_draw(s) for s in stmt.then_body):
            return True
        if stmt.else_body and any(stmt_contains_draw(s) for s in stmt.else_body):
            return True
    if isinstance(stmt, ast.For):
        return any(stmt_contains_draw(s) for s in stmt.body)
    return False


def split_loop_body(stmts: List[ast.Stmt]) -> Tuple[List[ast.Stmt], List[ast.Stmt], List[ast.Stmt]]:
    """Split loop body into pre, draw, and post sections."""
    def find_first(acc: List[ast.Stmt], remaining: List[ast.Stmt]) -> Tuple[List[ast.Stmt], List[ast.Stmt], List[ast.Stmt]]:
        if not remaining:
            return list(reversed(acc)), [], []
        s = remaining[0]
        if is_draw_stmt(s) or stmt_contains_draw(s):
            return list(reversed(acc)), remaining, []
        return find_first([s] + acc, remaining[1:])

    return find_first([], stmts)


def gen_clear(cfg: Config) -> str:
    """Generate clear background code."""
    rgba = cfg.bg_color if cfg.bg_color else default_bg_color
    return f"        ClearBackground({color_literal(*rgba)});"


def gen_draw_block(env: Env, mode: str, cfg: Config, draw_stmts: List[ast.Stmt]) -> List[str]:
    """Generate draw block code."""
    draw_lines = []
    for s in draw_stmts:
        if isinstance(s, ast.ExprStmt):
            if isinstance(s.expr, ast.Call) and s.expr.name == "clear":
                args = s.expr.args
                if args and isinstance(args[0], ast.PosArg):
                    draw_lines.append(f"        ClearBackground({gen_expr(env, mode, args[0].expr)});")
                elif args and isinstance(args[0], ast.NameArg):
                    draw_lines.append(f"        ClearBackground({gen_expr(env, mode, args[0].expr)});")
                else:
                    draw_lines.append(gen_clear(cfg))
            else:
                draw_lines.append(f"        {gen_expr(env, mode, s.expr)};")
        elif isinstance(s, ast.Draw):
            draw_lines.append(f"        {gen_draw_call(env, mode, s.expr)}")
        else:
            _, ls = gen_stmt(env, mode, 2, s)
            draw_lines.extend(f"        {line}" if not line.startswith("        ") else line for line in ls)

    if mode == Mode.INTERACTIVE:
        return ["        BeginDrawing();"] + draw_lines + ["        EndDrawing();"]
    else:
        return (["        BeginTextureMode(target);"] +
                draw_lines +
                ["        EndTextureMode();",
                 "        Image _img = LoadImageFromTexture(target.texture);",
                 "        fwrite(_img.data, WIDTH * HEIGHT * 4, 1, _pipe);",
                 "        UnloadImage(_img);",
                 "        if (f % FPS == 0)",
                 "            TraceLog(LOG_INFO, \"Rendering... %d / %d seconds\", f / FPS, DURATION);"])


def gen_event_cond(env: Env, mode: str, e: ast.Expr) -> str:
    """Generate event condition code."""
    return gen_expr(env, mode, e)


def gen_event_block(env: Env, mode: str, trigger: ast.Expr, body: List[ast.Stmt]) -> List[str]:
    """Generate event block code."""
    cond = gen_event_cond(env, mode, trigger)
    _, body_lines = gen_stmts(env, mode, 2, body)
    return [f"        if ({cond}) {{"] + body_lines + ["        }"]


def gen_time_block(env: Env, mode: str, interval: ast.Expr, body: List[ast.Stmt]) -> List[str]:
    """Generate time block code."""
    interval_s = gen_expr(env, mode, interval)
    _, body_lines = gen_stmts(env, mode, 2, body)
    return [f"        if (fmodf(sim_time, {interval_s}) < dt) {{"] + body_lines + ["        }"]


def infer_return_type(env: Env, body: List[ast.Stmt]) -> Optional[str]:
    """Infer the return type of a function."""
    def scan(env_acc: Env, stmts: List[ast.Stmt]) -> Optional[str]:
        for stmt in stmts:
            if isinstance(stmt, ast.Return):
                if stmt.expr:
                    # Try to infer from expression
                    # Use a simple approach
                    return "float"
                return CType.VOID
            elif isinstance(stmt, ast.Let):
                # Add to env
                env_acc = env_acc.add(stmt.name, "float")
                continue
            elif isinstance(stmt, ast.If):
                if stmt.then_body:
                    t = scan(env_acc, stmt.then_body)
                    if t and t != CType.VOID:
                        return t
                if stmt.else_body:
                    t = scan(env_acc, stmt.else_body)
                    if t and t != CType.VOID:
                        return t
        return CType.VOID

    return scan(env, body)


def gen_fn_decl(env: Env, mode: str, name: str, params: List[Tuple[str, Optional[ast.TypeExpr]]], body: List[ast.Stmt]) -> str:
    """Generate C code for a function declaration."""
    ret_type = infer_return_type(env, body) or CType.VOID

    def c_type_str_of_type_expr(te: Optional[ast.TypeExpr]) -> str:
        if te is None:
            return "float"
        if isinstance(te, ast.TPrim):
            mapping = {
                "Num": "float",
                "Vec2": "Vector2",
                "Vec3": "Vector3",
                "Color": "Color",
                "Str": "char*",
                "Bool": "bool",
            }
            return mapping.get(te.name, "float")
        elif isinstance(te, ast.TArray):
            if isinstance(te.element, ast.TPrim) and te.element.name == "Vec2":
                return "vector_v2*"
            elif isinstance(te.element, ast.TPrim) and te.element.name == "Vec3":
                return "vector_v3*"
            return "vector*"
        elif isinstance(te, ast.TTuple):
            return "float*"
        return "float"

    def c_type_enum_of_type_expr(te: Optional[ast.TypeExpr]) -> str:
        if te is None:
            return CType.FLOAT
        if isinstance(te, ast.TPrim):
            mapping = {
                "Num": CType.FLOAT,
                "Vec2": CType.VECTOR2,
                "Vec3": CType.VECTOR3,
                "Color": CType.COLOR,
                "Str": CType.STRING,
                "Bool": CType.BOOL,
            }
            return mapping.get(te.name, CType.FLOAT)
        elif isinstance(te, ast.TArray):
            if isinstance(te.element, ast.TPrim) and te.element.name == "Vec2":
                return "vector_v2*"
            elif isinstance(te.element, ast.TPrim) and te.element.name == "Vec3":
                return "vector_v3*"
            return "vector*"
        elif isinstance(te, ast.TTuple):
            return CType.FLOAT
        return CType.FLOAT

    if not params:
        param_str = "void"
    else:
        param_strs = []
        for p, te in params:
            p_type = c_type_str_of_type_expr(te)
            param_strs.append(f"{p_type} {p}")
        param_str = ", ".join(param_strs)

    header = f"{ret_type} {name}({param_str}) {{"

    fn_env = env
    for p, te in params:
        fn_env = fn_env.add(p, c_type_enum_of_type_expr(te))

    _, body_lines = gen_stmts(fn_env, mode, 1, body)

    return "\n".join([header] + body_lines + ["}"])


def gen_headers(cfg: Config) -> List[str]:
    """Generate header includes and definitions."""
    lines = [
        '#include "raylib.h"',
        '#include "raymath.h"',
        '#include <stdio.h>',
        '#include <math.h>',
        '#include <stdbool.h>',
        '#include <string.h>',
        '#include <stdlib.h>',
        '',
        '/* --- dynamic array runtime --- */',
        'typedef struct { float   *data; int size; int capacity; } vector;',
        'typedef struct { Vector2 *data; int size; int capacity; } vector_v2;',
        'typedef struct { Vector3 *data; int size; int capacity; } vector_v3;',
        'static vector* create(int init) {',
        '    vector *v = (vector*)malloc(sizeof(vector));',
        '    v->data = (float*)malloc((init > 0 ? init : 4) * sizeof(float));',
        '    v->size = 0; v->capacity = (init > 0 ? init : 4);',
        '    return v;',
        '}',
        'static void push(vector *v, float val) {',
        '    if (v->size >= v->capacity) {',
        '        v->capacity *= 2;',
        '        v->data = (float*)realloc(v->data, v->capacity * sizeof(float));',
        '    }',
        '    v->data[v->size++] = val;',
        '}',
        'static float get(vector *v, int i) {',
        '    return (i >= 0 && i < v->size) ? v->data[i] : 0.0f;',
        '}',
        'static vector_v2* create_v2(int init) {',
        '    vector_v2 *v = (vector_v2*)malloc(sizeof(vector_v2));',
        '    v->data = (Vector2*)malloc((init > 0 ? init : 4) * sizeof(Vector2));',
        '    v->size = 0; v->capacity = (init > 0 ? init : 4);',
        '    return v;',
        '}',
        'static void push_v2(vector_v2 *v, Vector2 val) {',
        '    if (v->size >= v->capacity) {',
        '        v->capacity *= 2;',
        '        v->data = (Vector2*)realloc(v->data, v->capacity * sizeof(Vector2));',
        '    }',
        '    v->data[v->size++] = val;',
        '}',
        'static Vector2 get_v2(vector_v2 *v, int i) {',
        '    return (i >= 0 && i < v->size) ? v->data[i] : (Vector2){0};',
        '}',
        'static vector_v3* create_v3(int init) {',
        '    vector_v3 *v = (vector_v3*)malloc(sizeof(vector_v3));',
        '    v->data = (Vector3*)malloc((init > 0 ? init : 4) * sizeof(Vector3));',
        '    v->size = 0; v->capacity = (init > 0 ? init : 4);',
        '    return v;',
        '}',
        'static void push_v3(vector_v3 *v, Vector3 val) {',
        '    if (v->size >= v->capacity) {',
        '        v->capacity *= 2;',
        '        v->data = (Vector3*)realloc(v->data, v->capacity * sizeof(Vector3));',
        '    }',
        '    v->data[v->size++] = val;',
        '}',
        'static Vector3 get_v3(vector_v3 *v, int i) {',
        '    return (i >= 0 && i < v->size) ? v->data[i] : (Vector3){0};',
        '}',
        '/* ------------------------------ */',
        '',
        f'#define WIDTH    {cfg.width}',
        f'#define HEIGHT   {cfg.height}',
        f'#define FPS      {cfg.fps}',
    ]

    if cfg.duration is not None:
        lines.append(f'#define DURATION {cfg.duration}')
        lines.append('#define FRAMES   (FPS * DURATION)')

    return lines


def gen_window_init(cfg: Config, output_file: str) -> List[str]:
    """Generate window initialization code."""
    if cfg.mode == Mode.INTERACTIVE:
        return [
            '    SetTraceLogLevel(LOG_NONE);',
            f'    InitWindow(WIDTH, HEIGHT, "{cfg.title}");',
            '    SetTargetFPS(FPS);',
        ]
    else:
        return [
            '    SetConfigFlags(FLAG_WINDOW_HIDDEN);',
            '    SetTraceLogLevel(LOG_NONE);',
            f'    InitWindow(WIDTH, HEIGHT, "{cfg.title}");',
            '    RenderTexture2D target = LoadRenderTexture(WIDTH, HEIGHT);',
            '    FILE *_pipe = popen(',
            '        "ffmpeg -y"',
            '        " -f rawvideo"',
            '        " -pixel_format rgba"',
            f'        " -video_size {cfg.width}x{cfg.height}"',
            f'        " -framerate {cfg.fps}"',
            '        " -i pipe:0"',
            '        " -vf vflip"',
            '        " -c:v libx264"',
            '        " -pix_fmt yuv420p"',
            '        " -crf 18"',
            f'        " {output_file}",',
            '        "w"',
            '    );',
            '    if (!_pipe) {',
            '        TraceLog(LOG_ERROR, "Failed to open ffmpeg pipe");',
            '        return 1;',
            '    }',
        ]


def gen_frame_loop_header(cfg: Config) -> List[str]:
    """Generate frame loop header."""
    if cfg.mode == Mode.INTERACTIVE:
        return [
            '    while (!WindowShouldClose()) {',
            '        float dt = GetFrameTime();',
            '        sim_time += dt;',
        ]
    else:
        return [
            '    float dt = 1.0f / FPS;',
            '    for (int f = 0; f < FRAMES; f++) {',
            '        sim_time += dt;',
        ]


def gen_frame_loop_footer(cfg: Config) -> List[str]:
    """Generate frame loop footer."""
    if cfg.mode == Mode.INTERACTIVE:
        return ['    }']
    else:
        return [
            '    }',
            '    pclose(_pipe);',
            '    UnloadRenderTexture(target);',
        ]


def gen_cleanup() -> List[str]:
    """Generate cleanup code."""
    return [
        '    CloseWindow();',
        '    return 0;',
    ]


def gen_program(prog: ast.Program, video_output: Optional[str]) -> str:
    """Generate C code for a program."""
    cfg = extract_config(prog.config)

    global_stmts = []
    fn_decls = []
    loop_blocks = []
    event_blocks = []
    time_blocks = []
    for item in prog.items:
        # Check if it's a statement by looking at its type
        if isinstance(item, (ast.Let, ast.Return, ast.Draw, ast.If, ast.For, ast.Assign, ast.ExprStmt)):
            global_stmts.append(item)
        elif isinstance(item, ast.FnDecl):
            fn_decls.append(item)
        elif isinstance(item, ast.LoopBlock):
            loop_blocks.append(item.body)
        elif isinstance(item, ast.EventBlock):
            event_blocks.append((item.trigger, item.body))
        elif isinstance(item, ast.TimeBlock):
            time_blocks.append((item.interval, item.body))
        else:
            # Fallback - might be a wrapped Stmt
            if hasattr(item, 'stmt'):
                global_stmts.append(item.stmt)
        # Build function environment
    fn_env_entries = []
    for fn in fn_decls:
        params_env = []
        for p, te in fn.params:
            ct = ctype_of_typ(type_expr_to_typ(te)) if te else CType.FLOAT
            params_env.append((p, ct))
        # Use the first param env for inference (simplified)
        ret_ct = infer_return_type(Env(params_env), fn.body) or CType.FLOAT
        fn_env_entries.append((fn.name, ret_ct))

    global_env = Env()
    for name, ct in fn_env_entries:
        global_env = global_env.add(name, ct)

    for stmt in global_stmts:
        if isinstance(stmt, ast.Let):
            t = "float"  # Default
            global_env = global_env.add(stmt.name, t)

    # Generate global variable declarations
    global_var_lines = []
    for stmt in global_stmts:
        if isinstance(stmt, ast.Let):
            _, lines = gen_stmt(Env(), cfg.mode, 1, stmt)
            global_var_lines.extend(lines)

    # Generate global execution lines (non-let statements)
    global_exec_lines = []
    for stmt in global_stmts:
        if not isinstance(stmt, ast.Let):
            _, lines = gen_stmt(global_env, cfg.mode, 1, stmt)
            global_exec_lines.extend(lines)

    # Generate function declarations
    fn_decl_strs = []
    for fn in fn_decls:
        fn_decl_strs.append(gen_fn_decl(global_env, cfg.mode, fn.name, fn.params, fn.body))

    # Generate loop body
    loop_body_lines = []
    if loop_blocks:
        body = loop_blocks[0]
        pre, draw, post = split_loop_body(body)
        _, pre_lines = gen_stmts(global_env, cfg.mode, 2, pre)
        draw_lines = gen_draw_block(global_env, cfg.mode, cfg, draw)
        _, post_lines = gen_stmts(global_env, cfg.mode, 2, post)
        loop_body_lines = pre_lines + draw_lines + post_lines

    # Generate event blocks
    event_lines = []
    for trigger, body in event_blocks:
        event_lines.extend(gen_event_block(global_env, cfg.mode, trigger, body))

    # Generate time blocks
    time_lines = []
    for interval, body in time_blocks:
        time_lines.extend(gen_time_block(global_env, cfg.mode, interval, body))

    # Build the complete program
    output_path = video_output if video_output else "output.mp4"

    parts = (
        gen_headers(cfg) +
        [""] +
        ['static int key_from_name(const char *name) {',
         '    if (strcmp(name, "SPACE") == 0)    return KEY_SPACE;',
         '    if (strcmp(name, "ENTER") == 0)    return KEY_ENTER;',
         '    if (strcmp(name, "LEFT") == 0)     return KEY_LEFT;',
         '    if (strcmp(name, "RIGHT") == 0)    return KEY_RIGHT;',
         '    if (strcmp(name, "UP") == 0)       return KEY_UP;',
         '    if (strcmp(name, "DOWN") == 0)     return KEY_DOWN;',
         '    if (strcmp(name, "ESCAPE") == 0)   return KEY_ESCAPE;',
         '    if (strlen(name) == 1 && name[0] >= \'A\' && name[0] <= \'Z\')',
         '        return KEY_A + (name[0] - \'A\');',
         '    if (strlen(name) == 1 && name[0] >= \'0\' && name[0] <= \'9\')',
         '        return KEY_ZERO + (name[0] - \'0\');',
         '    return KEY_NULL;',
         '}',
         '',
         'char *to_string(float f) {',
         '    char *buf = malloc(32);',
         '    sprintf(buf, "%g", f);',
         '    return buf;',
         '}',
         '',
         'vector* range(int start, int end) {',
         '    vector* arr = create(end - start > 0 ? end - start : 4);',
         '    for (int i = start; i < end; i++) {',
         '        push(arr, (float)i);',
         '    }',
         '    return arr;',
         '}',
         '',
         'static int _lumen_perm[512];',
         'static int _lumen_noise_ready = 0;',
         'static void _lumen_noise_init(void) {',
         '    int p[256]; for (int i=0;i<256;i++) p[i]=i;',
         '    unsigned int s=12345;',
         '    for (int i=255;i>0;i--) { s=s*1664525u+1013904223u; int j=(int)((s>>16)%(i+1)); int t=p[i];p[i]=p[j];p[j]=t; }',
         '    for (int i=0;i<512;i++) _lumen_perm[i]=p[i&255];',
         '    _lumen_noise_ready=1;',
         '}',
         'static float _lumen_fade(float t){return t*t*t*(t*(t*6-15)+10);}',
         'static float _lumen_lerpf(float a,float b,float t){return a+t*(b-a);}',
         'static float _lumen_grad2(int h,float x,float y){switch(h&3){case 0:return x+y;case 1:return -x+y;case 2:return x-y;case 3:return -x-y;}return 0;}',
         'static float lumen_noise2(float x,float y){',
         '    if(!_lumen_noise_ready)_lumen_noise_init();',
         '    int xi=(int)floorf(x)&255,yi=(int)floorf(y)&255;',
         '    float xf=x-floorf(x),yf=y-floorf(y);',
         '    float u=_lumen_fade(xf),v=_lumen_fade(yf);',
         '    int aa=_lumen_perm[_lumen_perm[xi]+yi],ab=_lumen_perm[_lumen_perm[xi]+yi+1];',
         '    int ba=_lumen_perm[_lumen_perm[xi+1]+yi],bb=_lumen_perm[_lumen_perm[xi+1]+yi+1];',
         '    return _lumen_lerpf(_lumen_lerpf(_lumen_grad2(aa,xf,yf),_lumen_grad2(ba,xf-1,yf),u),',
         '                        _lumen_lerpf(_lumen_grad2(ab,xf,yf-1),_lumen_grad2(bb,xf-1,yf-1),u),v);',
         '}',
         'static float lumen_noise(float x){return lumen_noise2(x,0.0f);}',
         ''] +
        fn_decl_strs +
        ['',
         'int main(void) {'] +
        gen_window_init(cfg, output_path) +
        ['    float sim_time = 0.0f;'] +
        global_var_lines +
        global_exec_lines +
        [''] +
        gen_frame_loop_header(cfg) +
        event_lines +
        time_lines +
        loop_body_lines +
        gen_frame_loop_footer(cfg) +
        [''] +
        gen_cleanup() +
        ['}']
    )

    return '\n'.join(parts)