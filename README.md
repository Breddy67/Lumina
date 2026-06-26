# Lumina

A lightweight scripting language for real-time graphics and interactive animations, compiling to C via [Raylib](https://www.raylib.com/).

---

## Overview

Lumina (`.lm`) is a high-level, declarically-simple language designed for writing graphics programs without boilerplate. You describe shapes, motion, and events — Lumina handles the render loop, window management, and C compilation.

**Pipeline:**
```
.lm source → Tokeniser → Parser → Type Checker → C Codegen → GCC → Native Binary
```

---

## Installation

### Prerequisites

- Python 3.9+
- GCC
- Raylib (static library at `~/.lumen/raylib/`)

### Setup

```bash
git clone <repo>
cd lumina
pip install -r requirements.txt   # no external deps beyond stdlib
```

Raylib headers and `libraylib.a` must live at:
```
~/.lumen/raylib/include/
~/.lumen/raylib/lib/libraylib.a
```

---

## Usage

```bash
# Compile and run
python main.py run MyScene.lm

# Compile only (produces MyScene.c + MyScene binary)
python main.py build MyScene.lm

# Debug mode (prints tokens + AST)
python main.py -d run MyScene.lm

# Render to video
python main.py -o output.mp4 run MyScene.lm
```

Or use the quick runner (skips type checker):
```bash
python run_now.py MyScene.lm
```

---

## Language Reference

### Config Block

Every program can start with a `config` block:

```
config {
  width  = 800
  height = 600
  fps    = 60
  title  = "My Scene"
  mode   = interactive   // or: render
  duration = 10s         // required when mode = render
}
```

---

### Types

| Type | Description |
|------|-------------|
| `Num` | Floating-point number |
| `Bool` | `true` / `false` |
| `Str` | String literal |
| `Color` | Hex color, e.g. `#ff0000` or `#ff0000ff` |
| `Vec2` | 2D vector / tuple `(Num, Num)` |
| `Vec3` | 3D vector / tuple `(Num, Num, Num)` |
| `[T]` | Array of type `T` |

---

### Variables

```
let x = 10
let pos: Vec2 = (100, 200)
let name: Str = "hello"
```

---

### Control Flow

```
if (x > 0) {
  // ...
} else if (x == 0) {
  // ...
} else {
  // ...
}

for item in my_array {
  // ...
}
```

---

### Functions

```
fn distance(a: Vec2, b: Vec2) {
  let dx = a.x - b.x
  let dy = a.y - b.y
  return sqrt(dx * dx + dy * dy)
}
```

Parameters can optionally be type-annotated. Default parameter type when unannotated is `Num`.

---

### Drawing

Use `draw` with a shape constructor:

```
draw Circle((x, y), radius, color=#ff0000)
draw Rect((x, y), width, height, color=#00ff00)
draw Line((x1, y1), (x2, y2), color=#ffffff, thickness=2)
draw Triangle((x1,y1), (x2,y2), (x3,y3), color=#0000ff)
draw Arc((x, y), radius, start_angle, end_angle, color=#ff00ff)
draw Text("hello", (x, y), color=#ffffff, size=24)
draw Pixel((x, y), color=#ff0000)
draw Sprite(texture, (x, y), scale=1, rotation=0)
```

---

### Execution Blocks

```
// Runs every frame
loop {
  clear()
  draw Circle((200, 200), 50, color=#00ff00)
}

// Runs on an event
on mouse_clicked() {
  // handle click
}

// Runs on a timer
every 500ms {
  // fires every half second
}
```

---

### Built-in Variables

| Name | Type | Description |
|------|------|-------------|
| `time` | `Num` | Elapsed simulation time (seconds) |
| `dt` | `Num` | Delta time since last frame |
| `mouse` | `Vec2` | Current mouse position |
| `width` | `Num` | Canvas width |
| `height` | `Num` | Canvas height |
| `pi` | `Num` | π |
| `tau` | `Num` | 2π |

---

### Built-in Functions

#### Math
`sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `sqrt`, `pow`, `abs`,
`floor`, `ceil`, `round`, `min`, `max`, `clamp(v, lo, hi)`, `lerp(a, b, t)`,
`map(v, in_lo, in_hi, out_lo, out_hi)`, `random()`, `random(max)`, `random(min, max)`,
`noise(x)`, `noise2(x, y)`, `range(from, to)`

#### Vector
`length(v)`, `distance(a, b)`, `normalize(v)`, `dot(a, b)`, `angle(a, b)`

#### Input
```
is_key_pressed("space")    // one-shot press
is_key_down("left")        // held
is_key_released("right")
is_key_up("up")

mouse_clicked()            // left button one-shot
mouse_down()
mouse_released()
get_mouse_x()
get_mouse_y()
get_mouse_position()       // Vec2
get_mouse_wheel()
```

#### Utility
`clear()`, `clear(color)`, `print(...)`, `str(num)`, `push(array, value)`,
`get_fps()`, `get_screen_width()`, `get_screen_height()`

---

### Time Literals

```
1s        // 1 second
500ms     // 500 milliseconds
0.5s      // 0.5 seconds
```

---

### Imports

```
import myModule from "path/to/module.lm"
```

---

## Examples

### Bouncing Ball

```
config {
  width = 800
  height = 600
  title = "Bouncing Ball"
}

let px = 20
let py = 300
let vx = 10
let vy = 6
let r  = 20

loop {
  clear()
  vy = vy + 0.6
  px = px + vx
  py = py + vy

  if (py + r > 600) { py = 600 - r   vy = vy * -1 }
  if (px + r > 800) { px = 800 - r   vx = vx * -1 }
  else if (px - r < 0) { px = r   vx = vx * -1 }

  draw Circle((px, py), r, color=#00ff00)
}
```

### Fractal Tree

```
config {
  width = 600
  height = 600
  title = "Fractal Tree"
}

let root = (400, 580)

fn branch(pos: Vec2, ang, len, depth) {
  let rad = ang * (pi / 180)
  let end_pos = (pos.x + cos(rad) * len, pos.y + sin(rad) * len)
  draw Line(pos, end_pos, color=#ffffff)
  if (depth > 0) {
    branch(end_pos, ang - 20, len * 0.7, depth - 1)
    branch(end_pos, ang + 20, len * 0.7, depth - 1)
  }
}

loop {
  clear()
  branch(root, -90, 120, 7)
}
```

---

## Compiler Architecture

| Module | Role |
|--------|------|
| `tokeniser.py` | Lexes source into tokens (keywords, literals, operators) |
| `parser.py` | Recursive descent parser; produces AST (`lumina_ast.py`) |
| `checker.py` | Scoped type checker with diagnostics (errors + warnings) |
| `codegen.py` | Walks AST, emits C code using Raylib API |
| `predefined.py` | Built-in function signatures and their C implementations |
| `lumina_types.py` | Type system (`TNum`, `TBool`, `TTuple`, `TArray`, etc.) |
| `main.py` | CLI entry point (`build` / `run` subcommands) |
| `run_now.py` | Quick runner — skips type checker |
| `errors.py` | Structured error types and pretty printing |

---

## Diagnostics

The type checker emits structured diagnostics before compilation:

```
1 error(s), 2 warning(s)

[ERROR] function 'foo' — undefined variable 'bar'
[WARNING] top level — variable 'unused' is defined but never used
```

Errors block compilation. Warnings are informational.

---

## Render Mode

Set `mode = render` and a `duration` to export frames instead of opening a window:

```
config {
  width    = 1280
  height   = 720
  fps      = 60
  mode     = render
  duration = 5s
}
```

```bash
python main.py -o animation.mp4 run scene.lm
```

---

## License

MIT
