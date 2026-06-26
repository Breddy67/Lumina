# lumina/lumina_utils.py
"""Utility functions for the Lumina compiler."""

import os
import sys
from typing import List, Tuple, Callable, Any, Optional


def explode(s: str) -> List[str]:
    """Convert a string to a list of characters."""
    return list(s)


def implode(chars: List[str]) -> str:
    """Convert a list of characters to a string."""
    return ''.join(chars)


def read_file(filename: str) -> str:
    """Read the entire contents of a file."""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def is_alpha(c: str) -> bool:
    """Check if a character is alphabetic or underscore."""
    return ('a' <= c <= 'z') or ('A' <= c <= 'Z') or c == '_'


def is_digit(c: str) -> bool:
    """Check if a character is a digit."""
    return '0' <= c <= '9'


def is_alphanum(c: str) -> bool:
    """Check if a character is alphanumeric."""
    return is_alpha(c) or is_digit(c)


def compile_cmd(c_filename: str, basename: str) -> str:
    """Generate the compilation command for C code."""
    home_dir = os.environ.get('USERPROFILE') or os.environ.get('HOME') or '.'
    include_path = os.path.join(home_dir, '.lumen', 'raylib', 'include')
    lib_path = os.path.join(home_dir, '.lumen', 'raylib', 'lib')
    static_lib = os.path.join(lib_path, 'libraylib.a')

    if sys.platform == 'win32' or sys.platform == 'cygwin':
        return f'gcc {c_filename} -o {basename}.exe -I"{include_path}" "{static_lib}" -lopengl32 -lgdi32 -lwinmm'
    elif sys.platform == 'darwin':
        return f'gcc {c_filename} -o {basename} -I"{include_path}" "{static_lib}" -framework CoreVideo -framework IOKit -framework Cocoa -framework GLUT -framework OpenGL'
    else:
        return f'gcc {c_filename} -o {basename} -I"{include_path}" "{static_lib}" -lGL -lm -lpthread -ldl -lrt -lX11'