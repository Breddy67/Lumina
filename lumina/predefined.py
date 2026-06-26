# lumina/predefined.py
"""Predefined functions and variables for Lumina."""

from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any, Tuple
from lumina_types import Typ, TNum, TBool, TStr, TColor, TTime, TTuple, TArray, TVoid, TAny, TShape


@dataclass
class Entry:
    """Predefined function entry."""
    name: str
    arity: Optional[int]  # None for variadic
    ret: Typ
    arg_types: Optional[List[Typ]]
    impl: Optional[Callable[[List[str]], str]]
    allowed_named: Optional[List[str]]
    kind: str  # "Function" or "Constructor"


def fmt1(f: str, args: List[str]) -> str:
    return f % (args[0],)


def fmt2(f: str, args: List[str]) -> str:
    return f % (args[0], args[1])


def fmt3(f: str, args: List[str]) -> str:
    return f % (args[0], args[1], args[2])


def functions() -> List[Entry]:
    """Get the list of predefined functions."""
    return [
        # Math
        Entry("sin", 1, TNum(), [TNum()], lambda a: f"sinf({a[0]})", None, "Function"),
        Entry("cos", 1, TNum(), [TNum()], lambda a: f"cosf({a[0]})", None, "Function"),
        Entry("tan", 1, TNum(), [TNum()], lambda a: f"tanf({a[0]})", None, "Function"),
        Entry("asin", 1, TNum(), [TNum()], lambda a: f"asinf({a[0]})", None, "Function"),
        Entry("acos", 1, TNum(), [TNum()], lambda a: f"acosf({a[0]})", None, "Function"),
        Entry("atan", 1, TNum(), [TNum()], lambda a: f"atanf({a[0]})", None, "Function"),
        Entry("atan2", 2, TNum(), [TNum(), TNum()], lambda a: f"atan2f({a[0]}, {a[1]})", None, "Function"),
        Entry("sqrt", 1, TNum(), [TNum()], lambda a: f"sqrtf({a[0]})", None, "Function"),
        Entry("pow", 2, TNum(), [TNum(), TNum()], lambda a: f"powf({a[0]}, {a[1]})", None, "Function"),
        Entry("abs", 1, TNum(), [TNum()], lambda a: f"fabsf({a[0]})", None, "Function"),
        Entry("floor", 1, TNum(), [TNum()], lambda a: f"floorf({a[0]})", None, "Function"),
        Entry("ceil", 1, TNum(), [TNum()], lambda a: f"ceilf({a[0]})", None, "Function"),
        Entry("round", 1, TNum(), [TNum()], lambda a: f"roundf({a[0]})", None, "Function"),
        Entry("min", 2, TNum(), [TNum(), TNum()], lambda a: f"fminf({a[0]}, {a[1]})", None, "Function"),
        Entry("max", 2, TNum(), [TNum(), TNum()], lambda a: f"fmaxf({a[0]}, {a[1]})", None, "Function"),
        Entry("clamp", 3, TNum(), [TNum(), TNum(), TNum()], lambda a: f"Clamp({a[0]}, {a[1]}, {a[2]})", None, "Function"),
        Entry("lerp", 3, TNum(), [TNum(), TNum(), TNum()], lambda a: f"Lerp({a[0]}, {a[1]}, {a[2]})", None, "Function"),
        Entry("map", 5, TNum(), [TNum(), TNum(), TNum(), TNum(), TNum()],
              lambda a: f"Remap({a[0]}, {a[1]}, {a[2]}, {a[3]}, {a[4]})", None, "Function"),
        Entry("random", None, TNum(), None,
              lambda a: ("GetRandomValue(0, 100)" if not a else
                        f"GetRandomValue(0, (int)({a[0]}))" if len(a) == 1 else
                        f"GetRandomValue((int)({a[0]}), (int)({a[1]}))"),
              None, "Function"),
        Entry("range", 2, TArray(TNum()), [TNum(), TNum()],
              lambda a: f"range({a[0]}, {a[1]})", None, "Function"),
        Entry("noise", 1, TNum(), [TNum()],
              lambda a: f"lumen_noise({a[0]})", None, "Function"),
        Entry("noise2", 2, TNum(), [TNum(), TNum()],
              lambda a: f"lumen_noise2({a[0]}, {a[1]})", None, "Function"),

        # Vector helpers
        Entry("length", 1, TNum(), [TAny()],
              lambda a: f"Vector2Length({a[0]})", None, "Function"),
        Entry("distance", 2, TNum(), [TAny(), TAny()],
              lambda a: f"Vector2Distance({a[0]}, {a[1]})", None, "Function"),
        Entry("normalize", 1, TAny(), [TAny()],
              lambda a: f"Vector2Normalize({a[0]})", None, "Function"),
        Entry("dot", 2, TNum(), [TAny(), TAny()],
              lambda a: f"Vector2DotProduct({a[0]}, {a[1]})", None, "Function"),
        Entry("angle", 2, TNum(), [TAny(), TAny()],
              lambda a: f"Vector2Angle({a[0]}, {a[1]})", None, "Function"),

        # Keyboard input
        Entry("is_key_pressed", 1, TBool(), [TStr()],
              lambda a: f"IsKeyPressed(key_from_name({a[0]}))", None, "Function"),
        Entry("is_key_down", 1, TBool(), [TStr()],
              lambda a: f"IsKeyDown(key_from_name({a[0]}))", None, "Function"),
        Entry("is_key_released", 1, TBool(), [TStr()],
              lambda a: f"IsKeyReleased(key_from_name({a[0]}))", None, "Function"),
        Entry("is_key_up", 1, TBool(), [TStr()],
              lambda a: f"IsKeyUp(key_from_name({a[0]}))", None, "Function"),
        Entry("get_char_pressed", 0, TNum(), [],
              lambda a: "GetCharPressed()", None, "Function"),

        # Mouse input
        Entry("mouse_clicked", 0, TBool(), [],
              lambda a: "IsMouseButtonPressed(MOUSE_BUTTON_LEFT)", None, "Function"),
        Entry("mouse_down", 0, TBool(), [],
              lambda a: "IsMouseButtonDown(MOUSE_BUTTON_LEFT)", None, "Function"),
        Entry("mouse_released", 0, TBool(), [],
              lambda a: "IsMouseButtonReleased(MOUSE_BUTTON_LEFT)", None, "Function"),
        Entry("is_mouse_button_pressed", 1, TBool(), [TNum()],
              lambda a: f"IsMouseButtonPressed((int)({a[0]}))", None, "Function"),
        Entry("is_mouse_button_down", 1, TBool(), [TNum()],
              lambda a: f"IsMouseButtonDown((int)({a[0]}))", None, "Function"),
        Entry("is_mouse_button_released", 1, TBool(), [TNum()],
              lambda a: f"IsMouseButtonReleased((int)({a[0]}))", None, "Function"),
        Entry("get_mouse_x", 0, TNum(), [],
              lambda a: "(float)GetMouseX()", None, "Function"),
        Entry("get_mouse_y", 0, TNum(), [],
              lambda a: "(float)GetMouseY()", None, "Function"),
        Entry("get_mouse_position", 0, TAny(), [],
              lambda a: "GetMousePosition()", None, "Function"),
        Entry("get_mouse_wheel", 0, TNum(), [],
              lambda a: "GetMouseWheelMove()", None, "Function"),
        Entry("get_fps", 0, TNum(), [],
              lambda a: "(float)GetFPS()", None, "Function"),
        Entry("get_screen_width", 0, TNum(), [],
              lambda a: "(float)GetScreenWidth()", None, "Function"),
        Entry("get_screen_height", 0, TNum(), [],
              lambda a: "(float)GetScreenHeight()", None, "Function"),

        # Drawing constructors
        Entry("Circle", 2, TShape(), None, None, ["color"], "Constructor"),
        Entry("Rect", 3, TShape(), None, None, ["color"], "Constructor"),
        Entry("Line", 2, TShape(), None, None, ["color", "thickness"], "Constructor"),
        Entry("Triangle", 3, TShape(), None, None, ["color"], "Constructor"),
        Entry("Arc", 4, TShape(), None, None, ["color"], "Constructor"),
        Entry("Pixel", 1, TShape(), None, None, ["color"], "Constructor"),
        Entry("Text", 2, TShape(), [TStr(), TTuple([TNum(), TNum()])],
              None, ["color", "size", "font"], "Constructor"),
        Entry("Sprite", 2, TShape(), None, None, ["color", "scale", "rotation"], "Constructor"),

        # IO utilities
        Entry("print", None, TVoid(), None,
              lambda a: f"printf(\"{' '.join(['%g'] * len(a))}\\n\", {', '.join(a)})",
              None, "Function"),
        Entry("clear", None, TVoid(), None,
              lambda a: "ClearBackground(BLACK)" if not a else f"ClearBackground({a[0]})",
              None, "Function"),
        Entry("str", 1, TStr(), [TNum()],
              lambda a: f"to_string({a[0]})", None, "Function"),
        Entry("push", 2, TVoid(), [TArray(TNum()), TNum()],
              lambda a: f"push({a[0]}, {a[1]})", None, "Function"),
    ]


@dataclass
class VarEntry:
    """Predefined variable entry."""
    vname: str
    vexpr: str
    vtype: Optional[Typ]


def vars() -> List[VarEntry]:
    """Get the list of predefined variables."""
    return [
        VarEntry("pi", "PI", TNum()),
        VarEntry("tau", "(2.0f * PI)", TNum()),
        VarEntry("dt", "dt", TNum()),
        VarEntry("time", "sim_time", TNum()),
        VarEntry("mouse", "GetMousePosition()", TTuple([TNum(), TNum()])),
        VarEntry("MOUSE_LEFT", "MOUSE_BUTTON_LEFT", TNum()),
        VarEntry("MOUSE_RIGHT", "MOUSE_BUTTON_RIGHT", TNum()),
        VarEntry("MOUSE_MIDDLE", "MOUSE_BUTTON_MIDDLE", TNum()),
        VarEntry("width", "WIDTH", TNum()),
        VarEntry("height", "HEIGHT", TNum()),
    ]


def find(name: str) -> Optional[Entry]:
    """Find a predefined function by name."""
    for e in functions():
        if e.name == name:
            return e
    return None


def var_expr(name: str) -> Optional[str]:
    """Get the expression for a predefined variable."""
    for v in vars():
        if v.vname == name:
            return v.vexpr
    return None


def var_type(name: str) -> Optional[Typ]:
    """Get the type of a predefined variable."""
    for v in vars():
        if v.vname == name:
            return v.vtype
    return None


def builtin_arities() -> List[Tuple[str, Optional[int]]]:
    """Get the arities of all predefined functions."""
    return [(e.name, e.arity) for e in functions()]


def builtin_names() -> List[str]:
    """Get the names of all predefined functions."""
    return [e.name for e in functions()]