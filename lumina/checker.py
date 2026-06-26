# lumina/checker.py
"""Type checker for the Lumina language."""

from typing import List, Optional, Tuple, Dict, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict

import lumina_ast as ast
import lumina_types
import predefined
from lumina_types import Typ, TNum, TBool, TStr, TColor, TTime, TTuple, TArray, TStruct, TFn, TVoid, TAny, TShape, pp_typ
from errors import raise_type_error


class Severity:
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Diagnostic:
    severity: str
    message: str
    context: str


def error_diag(ctx: str, msg: str) -> Diagnostic:
    return Diagnostic(Severity.ERROR, msg, ctx)


def warn_diag(ctx: str, msg: str) -> Diagnostic:
    return Diagnostic(Severity.WARNING, msg, ctx)


def pp_diagnostic(d: Diagnostic) -> str:
    sev = "ERROR" if d.severity == Severity.ERROR else "WARNING"
    return f"[{sev}] {d.context} — {d.message}"


@dataclass
class Binding:
    typ: Typ
    used: bool = False


class Env:
    """Type environment with scopes."""
    def __init__(self):
        self.scopes: List[Dict[str, Binding]] = [{}]

    def push_scope(self) -> 'Env':
        self.scopes.insert(0, {})
        return self

    def pop_scope(self) -> None:
        if len(self.scopes) > 1:
            self.scopes.pop(0)

    def lookup(self, name: str) -> Optional[Binding]:
        for scope in self.scopes:
            if name in scope:
                return scope[name]
        return None

    def lookup_local(self, name: str) -> Optional[Binding]:
        if self.scopes:
            return self.scopes[0].get(name)
        return None

    def lookup_outer(self, name: str) -> Optional[Binding]:
        if len(self.scopes) >= 2:
            for scope in self.scopes[1:]:
                if name in scope:
                    return scope[name]
        return None

    def define(self, name: str, typ: Typ) -> bool:
        if self.scopes:
            if name in self.scopes[0]:
                return True  # Duplicate
            self.scopes[0][name] = Binding(typ)
            return False
        return False

    def mark_used(self, name: str) -> bool:
        b = self.lookup(name)
        if b:
            b.used = True
            return True
        return False

    def unused_in_scope(self) -> List[str]:
        if self.scopes:
            return [name for name, b in self.scopes[0].items() if not b.used]
        return []


@dataclass
class CheckerState:
    diags: List[Diagnostic] = field(default_factory=list)
    in_function: bool = False
    in_loop_or_event: bool = False
    context: str = "top level"

    def emit(self, d: Diagnostic) -> None:
        self.diags.append(d)

    def error(self, msg: str) -> None:
        self.emit(error_diag(self.context, msg))

    def warn(self, msg: str) -> None:
        self.emit(warn_diag(self.context, msg))


# Type compatibility functions
def types_compatible(a: Typ, b: Typ) -> bool:
    """Check if two types are compatible."""
    if isinstance(a, TAny) or isinstance(b, TAny):
        return True
    if isinstance(a, TTuple) and isinstance(b, TTuple):
        if len(a.elements) != len(b.elements):
            return False
        return all(types_compatible(x, y) for x, y in zip(a.elements, b.elements))
    if isinstance(a, TArray) and isinstance(b, TArray):
        return types_compatible(a.element_type, b.element_type)
    if isinstance(a, TStruct) and isinstance(b, TStruct):
        if a.name != b.name:
            return False
        if len(a.fields) != len(b.fields):
            return False
        a_fields = {name: typ for name, typ in a.fields}
        b_fields = {name: typ for name, typ in b.fields}
        for name, typ in a_fields.items():
            if name not in b_fields:
                return False
            if not types_compatible(typ, b_fields[name]):
                return False
        return True
    return type(a) is type(b) and a == b


def join_types(a: Typ, b: Typ) -> Typ:
    """Join two types."""
    if types_compatible(a, b):
        if isinstance(a, TAny):
            return b
        if isinstance(b, TAny):
            return a
        return a
    return TAny()


def additive_result(a: Typ, b: Typ) -> Optional[Typ]:
    """Get the result type of an additive operation."""
    if isinstance(a, TNum) and isinstance(b, TNum):
        return TNum()
    if isinstance(a, TTuple) and isinstance(b, TTuple):
        if len(a.elements) == len(b.elements):
            results = []
            for x, y in zip(a.elements, b.elements):
                r = additive_result(x, y)
                if r is None:
                    return None
                results.append(r)
            return TTuple(results)
    if isinstance(a, TAny) and isinstance(b, TNum):
        return TNum()
    if isinstance(a, TNum) and isinstance(b, TAny):
        return TNum()
    if isinstance(a, TAny) and isinstance(b, TTuple):
        return b
    if isinstance(a, TTuple) and isinstance(b, TAny):
        return a
    if isinstance(a, TAny) and isinstance(b, TAny):
        return TAny()
    return None


def tuple_field_type(field: str, elements: List[Typ]) -> Optional[Typ]:
    """Get the type of a tuple field."""
    idx = {"x": 0, "y": 1, "z": 2, "w": 3}.get(field)
    if idx is not None and idx < len(elements):
        return elements[idx]
    return None


def tuple_index_type(idx_expr: ast.Expr, elements: List[Typ]) -> Optional[Typ]:
    """Get the type of a tuple index."""
    if isinstance(idx_expr, ast.Num) and idx_expr.value.is_integer():
        i = int(idx_expr.value)
        if 0 <= i < len(elements):
            return elements[i]
        return None
    # Non-constant index: return join of all element types
    return join_types(TAny(), TAny())


# Built-in functions
builtin_functions: List[Tuple[str, Typ]] = [(name, TFn(arity) if arity is not None else TAny())
                                             for name, arity in predefined.builtin_arities()]


def check_config_expr(env: Env, st: CheckerState, expr: ast.Expr) -> Typ:
    """Check a config expression."""
    if isinstance(expr, ast.Ident):
        return TAny()
    return check_expr(env, st, expr)


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
        if te.name in mapping:
            return mapping[te.name]
        raise_type_error(f"Unknown primitive type '{te.name}'")
    elif isinstance(te, ast.TArray):
        return TArray(type_expr_to_typ(te.element))
    elif isinstance(te, ast.TTuple):
        return TTuple([type_expr_to_typ(e) for e in te.elements])
    return TAny()


def is_predefined(name: str) -> bool:
    """Check if a name is predefined."""
    return any(e.name == name for e in predefined.functions()) or any(v.vname == name for v in predefined.vars())


# Expression checker
def check_expr(env: Env, st: CheckerState, expr: ast.Expr) -> Typ:
    """Check an expression and return its type."""
    if isinstance(expr, ast.Num):
        return TNum()
    elif isinstance(expr, ast.Str):
        return TStr()
    elif isinstance(expr, ast.Bool):
        return TBool()
    elif isinstance(expr, ast.ColorLiteral):
        return TColor()
    elif isinstance(expr, ast.Time):
        return TTime()
    elif isinstance(expr, ast.Ident):
        b = env.lookup(expr.name)
        if b:
            env.mark_used(expr.name)
            return b.typ
        var_t = predefined.var_type(expr.name)
        if var_t is not None:
            return var_t
        st.error(f"undefined variable '{expr.name}'")
        return TAny()
    elif isinstance(expr, ast.Tuple):
        elems = [check_expr(env, st, expr.first),
                 check_expr(env, st, expr.second)]
        elems.extend(check_expr(env, st, e) for e in expr.rest)
        return TTuple(elems)
    elif isinstance(expr, ast.Array):
        elem_typ = TAny()
        for e in expr.elements:
            elem_typ = join_types(elem_typ, check_expr(env, st, e))
        return TArray(elem_typ)
    elif isinstance(expr, ast.Unop):
        if expr.op == ast.UnOp.NEG:
            t = check_expr(env, st, expr.expr)
            if not types_compatible(t, TNum()):
                st.error(f"unary '-' requires a numeric operand, got {pp_typ(t)}")
            return TNum()
        elif expr.op == ast.UnOp.NOT:
            t = check_expr(env, st, expr.expr)
            if not types_compatible(t, TBool()):
                st.error(f"unary '!' requires a bool operand, got {pp_typ(t)}")
            return TBool()
    elif isinstance(expr, ast.Binop):
        return check_binop(env, st, expr.op, expr.left, expr.right)
    elif isinstance(expr, ast.Call):
        env.mark_used(expr.name)

        pos_args = [arg.expr for arg in expr.args if isinstance(arg, ast.PosArg)]
        named_args = [(arg.name, arg.expr) for arg in expr.args if isinstance(arg, ast.NameArg)]

        # Check against predefined functions
        pred = predefined.find(expr.name)
        if pred:
            if pred.arity is not None and len(pos_args) != pred.arity:
                st.error(f"function '{expr.name}' expects {pred.arity} argument(s), got {len(pos_args)}")

            if pred.arg_types:
                for i, expected in enumerate(pred.arg_types):
                    if i < len(pos_args):
                        actual = check_expr(env, st, pos_args[i])
                        if not types_compatible(actual, expected):
                            st.error(f"argument {i+1} of '{expr.name}' expects {pp_typ(expected)}, got {pp_typ(actual)}")

            for _, e in named_args:
                check_expr(env, st, e)

            return pred.ret

        # Not predefined - check in environment
        b = env.lookup(expr.name)
        if b:
            if isinstance(b.typ, TFn):
                if len(pos_args) != b.typ.arity:
                    st.error(f"function '{expr.name}' expects {b.typ.arity} argument(s), got {len(pos_args)}")
            else:
                st.error(f"'{expr.name}' is not a function (type {pp_typ(b.typ)})")
        else:
            st.error(f"undefined function '{expr.name}'")

        for arg in expr.args:
            if isinstance(arg, ast.PosArg):
                check_expr(env, st, arg.expr)
            else:
                check_expr(env, st, arg.expr)

        return TAny()
    elif isinstance(expr, ast.Struct):
        seen = set()
        checked_fields = []
        for field, e in expr.fields:
            if field in seen:
                st.error(f"duplicate field '{field}' in struct '{expr.name}'")
            seen.add(field)
            checked_fields.append((field, check_expr(env, st, e)))

        if expr.name == "Vec2":
            return TTuple([TNum(), TNum()])
        elif expr.name == "Vec3":
            return TTuple([TNum(), TNum(), TNum()])
        else:
            return TStruct(expr.name, checked_fields)
    elif isinstance(expr, ast.Access):
        t = check_expr(env, st, expr.base)
        for suffix in expr.suffixes:
            t = check_access_suffix(env, st, t, suffix)
        return t

    return TAny()


def check_access_suffix(env: Env, st: CheckerState, base_typ: Typ, suffix: ast.AccessSuffix) -> Typ:
    """Check an access suffix and return the resulting type."""
    if isinstance(suffix, ast.Field):
        if isinstance(base_typ, TStruct):
            fields = {name: typ for name, typ in base_typ.fields}
            if suffix.name in fields:
                return fields[suffix.name]
            st.error(f"struct '{base_typ.name}' has no field '{suffix.name}'")
            return TAny()
        elif isinstance(base_typ, TTuple):
            t = tuple_field_type(suffix.name, base_typ.elements)
            if t is not None:
                return t
            st.warn(f"tuple has no field '{suffix.name}'")
            return TAny()
        elif isinstance(base_typ, TAny):
            return TAny()
        else:
            st.warn(f"field access on non-struct/tuple type {pp_typ(base_typ)}")
            return TAny()
    elif isinstance(suffix, ast.Index):
        it = check_expr(env, st, suffix.expr)
        if not types_compatible(it, TNum()):
            st.error(f"array index must be numeric, got {pp_typ(it)}")

        if isinstance(base_typ, TArray):
            return base_typ.element_type
        elif isinstance(base_typ, TTuple):
            t = tuple_index_type(suffix.expr, base_typ.elements)
            if t is not None:
                return t
            st.warn("tuple index is out of bounds")
            return TAny()
        elif isinstance(base_typ, TStr):
            return TStr()
        elif isinstance(base_typ, TAny):
            return TAny()
        else:
            st.warn(f"index access on non-array type {pp_typ(base_typ)}")
            return TAny()

    return TAny()


def check_binop(env: Env, st: CheckerState, op: str, left: ast.Expr, right: ast.Expr) -> Typ:
    """Check a binary operation."""
    lt = check_expr(env, st, left)
    rt = check_expr(env, st, right)

    if op in [ast.BinOp.ADD, ast.BinOp.SUB]:
        r = additive_result(lt, rt)
        if r is not None:
            return r
        st.error(f"arithmetic op requires matching numeric or tuple operands, got {pp_typ(lt)} and {pp_typ(rt)}")
        return TAny()
    elif op in [ast.BinOp.MUL, ast.BinOp.DIV]:
        if not types_compatible(lt, TNum()):
            st.error(f"left operand of arithmetic op must be numeric, got {pp_typ(lt)}")
        if not types_compatible(rt, TNum()):
            st.error(f"right operand of arithmetic op must be numeric, got {pp_typ(rt)}")
        return TNum()
    elif op in [ast.BinOp.LT, ast.BinOp.GT, ast.BinOp.LTEQ, ast.BinOp.GTEQ]:
        if not types_compatible(lt, TNum()):
            st.error(f"left operand of comparison must be numeric, got {pp_typ(lt)}")
        if not types_compatible(rt, TNum()):
            st.error(f"right operand of comparison must be numeric, got {pp_typ(rt)}")
        return TBool()
    elif op in [ast.BinOp.EQ, ast.BinOp.NOT_EQ]:
        if not types_compatible(lt, rt):
            st.error(f"equality operands have incompatible types: {pp_typ(lt)} vs {pp_typ(rt)}")
        return TBool()
    elif op in [ast.BinOp.AND, ast.BinOp.OR]:
        if not types_compatible(lt, TBool()):
            st.error(f"left operand of logical op must be bool, got {pp_typ(lt)}")
        if not types_compatible(rt, TBool()):
            st.error(f"right operand of logical op must be bool, got {pp_typ(rt)}")
        return TBool()

    return TAny()


def check_not_bare_literal(st: CheckerState, kw: str, expr: ast.Expr) -> None:
    """Warn if a bare literal is used."""
    if isinstance(expr, ast.Num):
        st.warn(f"'{kw}' called with a bare number literal")


# Statement checker
def check_stmt(env: Env, st: CheckerState, stmt: ast.Stmt) -> None:
    """Check a statement."""
    if isinstance(stmt, ast.Let):
        t = check_expr(env, st, stmt.expr)
        if stmt.type_annotation:
            annotated_t = type_expr_to_typ(stmt.type_annotation)
            if not types_compatible(t, annotated_t):
                st.error(f"type annotation mismatch: expected {pp_typ(annotated_t)} but got {pp_typ(t)}")

        dup_local = env.lookup_local(stmt.name) is not None
        shadows_outer = (not dup_local) and env.lookup_outer(stmt.name) is not None

        env.define(stmt.name, t)

        if dup_local:
            st.warn(f"variable '{stmt.name}' is already defined in this scope")
        elif shadows_outer:
            st.warn(f"variable '{stmt.name}' shadows an existing binding")

    elif isinstance(stmt, ast.Return):
        if not st.in_function:
            st.error("'return' used outside a function body")
        if stmt.expr:
            check_expr(env, st, stmt.expr)

    elif isinstance(stmt, ast.Draw):
        check_not_bare_literal(st, "draw", stmt.expr)
        check_expr(env, st, stmt.expr)

    elif isinstance(stmt, ast.If):
        ct = check_expr(env, st, stmt.cond)
        if not types_compatible(ct, TBool()):
            st.error(f"if condition must be bool, got {pp_typ(ct)}")
        check_block(env, st, stmt.then_body)
        if stmt.else_body:
            check_block(env, st, stmt.else_body)

    elif isinstance(stmt, ast.For):
        it = check_expr(env, st, stmt.iterable)
        if not (isinstance(it, TArray) or isinstance(it, TAny)):
            st.error(f"for-in iterable must be an array, got {pp_typ(it)}")

        inner_env = env.push_scope()
        inner_env.define(stmt.var, TAny())
        inner_st = CheckerState(
            diags=st.diags,
            in_function=st.in_function,
            in_loop_or_event=True,
            context=st.context
        )
        check_stmts(inner_env, inner_st, stmt.body)
        unused = inner_env.unused_in_scope()
        for name in unused:
            if name != stmt.var:
                inner_st.warn(f"variable '{name}' is defined but never used")

    elif isinstance(stmt, ast.Assign):
        b = env.lookup(stmt.accessor.name)
        if b is None:
            st.error(f"undefined variable '{stmt.accessor.name}'")
            base_typ = TAny()
        else:
            base_typ = b.typ

        if stmt.op in [ast.AssignOp.PLUS_SET, ast.AssignOp.MINUS_SET]:
            env.mark_used(stmt.accessor.name)

        lhs_typ = base_typ
        for suffix in stmt.accessor.suffixes:
            lhs_typ = check_access_suffix(env, st, lhs_typ, suffix)

        rt = check_expr(env, st, stmt.expr)

        if stmt.op in [ast.AssignOp.PLUS_SET, ast.AssignOp.MINUS_SET]:
            if additive_result(lhs_typ, rt) is None:
                st.error(f"+= / -= requires matching numeric or tuple operands, got {pp_typ(lhs_typ)} and {pp_typ(rt)}")
        else:  # Set
            if not types_compatible(lhs_typ, rt):
                st.error(f"assignment type mismatch: cannot assign {pp_typ(rt)} to {pp_typ(lhs_typ)}")

    elif isinstance(stmt, ast.ExprStmt):
        check_expr(env, st, stmt.expr)


def check_block(env: Env, st: CheckerState, stmts: List[ast.Stmt]) -> None:
    """Check a block of statements."""
    inner_env = env.push_scope()
    check_stmts(inner_env, st, stmts)
    unused = inner_env.unused_in_scope()
    for name in unused:
        st.warn(f"variable '{name}' is defined but never used")


def check_stmts(env: Env, st: CheckerState, stmts: List[ast.Stmt]) -> None:
    """Check a list of statements."""
    for stmt in stmts:
        check_stmt(env, st, stmt)


# Top-level checker
def check_top_level(env: Env, st: CheckerState, item: ast.TopLevel) -> None:
    """Check a top-level declaration."""
    if isinstance(item, ast.FnDecl):
        seen = set()
        for p, _ in item.params:
            if p in seen:
                st.error(f"duplicate parameter name '{p}'")
            seen.add(p)

        fn_env = env.push_scope()
        for p, te in item.params:
            t = type_expr_to_typ(te) if te else TNum()
            fn_env.define(p, t)

        fn_st = CheckerState(
            diags=st.diags,
            in_function=True,
            in_loop_or_event=st.in_loop_or_event,
            context=f"function '{item.name}'"
        )
        check_stmts(fn_env, fn_st, item.body)

        unused = fn_env.unused_in_scope()
        for name in unused:
            fn_st.warn(f"variable '{name}' is defined but never used")

    elif isinstance(item, ast.EventBlock):
        check_expr(env, st, item.trigger)
        ev_env = env.push_scope()
        ev_st = CheckerState(
            diags=st.diags,
            in_function=st.in_function,
            in_loop_or_event=True,
            context="event block"
        )
        check_stmts(ev_env, ev_st, item.body)
        unused = ev_env.unused_in_scope()
        for name in unused:
            ev_st.warn(f"variable '{name}' is defined but never used")

    elif isinstance(item, ast.TimeBlock):
        it = check_expr(env, st, item.interval)
        if not (isinstance(it, TNum) or isinstance(it, TStr) or isinstance(it, TTime) or isinstance(it, TAny)):
            st.error(f"'every' interval must be a numeric or time value, got {pp_typ(it)}")

        ev_env = env.push_scope()
        ev_st = CheckerState(
            diags=st.diags,
            in_function=st.in_function,
            in_loop_or_event=True,
            context="time block"
        )
        check_stmts(ev_env, ev_st, item.body)
        unused = ev_env.unused_in_scope()
        for name in unused:
            ev_st.warn(f"variable '{name}' is defined but never used")

    elif isinstance(item, ast.LoopBlock):
        lp_env = env.push_scope()
        lp_st = CheckerState(
            diags=st.diags,
            in_function=st.in_function,
            in_loop_or_event=True,
            context="loop block"
        )
        check_stmts(lp_env, lp_st, item.body)
        unused = lp_env.unused_in_scope()
        for name in unused:
            lp_st.warn(f"variable '{name}' is defined but never used")

    elif isinstance(item, (ast.Let, ast.Return, ast.Draw, ast.If, ast.For, ast.Assign, ast.ExprStmt)):
        # It's a statement directly
        if isinstance(item, ast.Let):
            t = check_expr(env, st, item.expr)
            if item.type_annotation:
                annotated_t = type_expr_to_typ(item.type_annotation)
                if not types_compatible(t, annotated_t):
                    st.error(f"type annotation mismatch: expected {pp_typ(annotated_t)} but got {pp_typ(t)}")

            if env.lookup_local(item.name) is not None:
                st.error(f"top-level name '{item.name}' is already defined "
                         f"{'as a builtin' if is_predefined(item.name) else 'in this scope'}")
            env.define(item.name, t)
        else:
            check_stmt(env, st, item)

def check_config(env: Env, st: CheckerState, items: List[Tuple[str, ast.Expr]]) -> None:
    """Check config items."""
    seen = set()
    for key, expr in items:
        if key in seen:
            st.error(f"duplicate config key '{key}'")
        seen.add(key)
        t = check_config_expr(env, st, expr)
        env.define(key, t)


def check_config_constraints(st: CheckerState, items: List[Tuple[str, ast.Expr]]) -> None:
    """Check config constraints."""
    def find_cfg(k: str) -> Optional[ast.Expr]:
        for key, expr in items:
            if key == k:
                return expr
        return None

    # Check render mode constraints
    mode = find_cfg("mode")
    mode_is_render = False
    if mode is not None:
        if isinstance(mode, ast.Ident) and mode.name == "render":
            mode_is_render = True
        elif isinstance(mode, ast.Str) and mode.value == "render":
            mode_is_render = True

    if mode_is_render:
        duration = find_cfg("duration")
        if duration is None:
            st.error("config 'duration' is required when mode is 'render'")
        else:
            if isinstance(duration, ast.Num) and duration.value <= 0:
                st.error("config 'duration' must be > 0")
            elif isinstance(duration, ast.Time) and duration.value <= 0:
                st.error("config 'duration' must be > 0")
            elif isinstance(duration, ast.Ident):
                st.warn("config 'duration' should be a numeric or time literal")

    # Check positive numeric configs
    for key in ["fps", "width", "height"]:
        val = find_cfg(key)
        if val is not None:
            if isinstance(val, ast.Num) and val.value <= 0:
                st.error(f"config '{key}' must be > 0")
            elif isinstance(val, ast.Time) and val.value <= 0:
                st.error(f"config '{key}' must be > 0")


def check_imports(st: CheckerState, imports: List[ast.Import], env: Env, builtin_names: Set[str]) -> None:
    """Check imports."""
    seen = set()
    for imp in imports:
        if imp.name in seen:
            st.error(f"duplicate import name '{imp.name}'")
        seen.add(imp.name)

        if imp.from_path == "":
            st.error(f"import '{imp.name}' has an empty source path")

        if imp.name in builtin_names:
            st.error(f"import '{imp.name}' conflicts with a builtin of the same name")

        if imp.name not in seen and imp.name not in builtin_names:
            env.define(imp.name, TAny())


def builtin_name_table() -> Set[str]:
    """Get the set of builtin names."""
    return {name for name, _ in builtin_functions}


def register_function_names(env: Env, items: List[ast.TopLevel]) -> None:
    """Register function names in the environment."""
    for item in items:
        if isinstance(item, ast.FnDecl):
            if env.lookup_local(item.name) is None:
                env.define(item.name, TFn(len(item.params)))


def register_builtin_names(env: Env) -> None:
    """Register builtin names in the environment."""
    for name, typ in builtin_functions:
        env.define(name, typ)


def register_magic_consts(env: Env) -> None:
    """Register magic constants."""
    env.define("pi", TNum())


# Public entry point
def check(prog: ast.Program) -> List[Diagnostic]:
    """Check a program and return diagnostics."""
    env = Env()
    st = CheckerState(context="top level")

    builtin_names = builtin_name_table()

    # Register imports
    import_names = {imp.name for imp in prog.imports}
    config_names = {key for key, _ in prog.config}

    # Register builtins
    register_builtin_names(env)
    register_magic_consts(env)

    # Check imports
    check_imports(st, prog.imports, env, builtin_names)

    # Check config
    check_config(env, st, prog.config)
    check_config_constraints(st, prog.config)

    # Register functions
    register_function_names(env, prog.items)

    # Check function collisions
    fn_seen = set()
    for item in prog.items:
        if isinstance(item, ast.FnDecl):
            if item.name in fn_seen:
                st.error(f"duplicate function declaration '{item.name}'")
            else:
                if item.name in builtin_names:
                    st.error(f"function '{item.name}' conflicts with a builtin of the same name")
                elif item.name in import_names:
                    st.error(f"function '{item.name}' conflicts with an import of the same name")
                elif item.name in config_names:
                    st.error(f"function '{item.name}' conflicts with a config key of the same name")
                fn_seen.add(item.name)

    # Check top-level items
    for item in prog.items:
        check_top_level(env, st, item)

    # Sort diagnostics: errors first, then warnings
    errors = [d for d in st.diags if d.severity == Severity.ERROR]
    warnings = [d for d in st.diags if d.severity == Severity.WARNING]
    return errors + warnings


def print_diagnostics(diags: List[Diagnostic]) -> None:
    """Print diagnostics."""
    if not diags:
        print("✓ No issues found.")
        return

    errors = [d for d in diags if d.severity == Severity.ERROR]
    warnings = [d for d in diags if d.severity == Severity.WARNING]
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)\n")
    for d in diags:
        print(pp_diagnostic(d))