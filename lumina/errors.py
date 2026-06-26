"""Error handling for the Lumina compiler."""

from enum import Enum, auto


class ErrorCategory(Enum):
    """Categories of errors."""
    PARSE_ERROR = auto()
    TOKENIZE_ERROR = auto()
    TYPE_ERROR = auto()
    CODGEN_ERROR = auto()
    RUNTIME_ERROR = auto()


class LuminaError(Exception):
    """A compiler error."""
    def __init__(self, category: ErrorCategory, message: str):
        self.category = category
        self.message = message
        super().__init__(message)

    def pp(self) -> str:
        """Pretty print the error."""
        category_names = {
            ErrorCategory.PARSE_ERROR: "Parse Error",
            ErrorCategory.TOKENIZE_ERROR: "Tokenization Error",
            ErrorCategory.TYPE_ERROR: "Type Error",
            ErrorCategory.CODGEN_ERROR: "Codegen Error",
            ErrorCategory.RUNTIME_ERROR: "Runtime Error",
        }
        return f"[{category_names[self.category]}] {self.message}"


def raise_parse_error(msg: str) -> None:
    """Raise a parse error."""
    raise LuminaError(ErrorCategory.PARSE_ERROR, msg)


def raise_tokenize_error(msg: str) -> None:
    """Raise a tokenization error."""
    raise LuminaError(ErrorCategory.TOKENIZE_ERROR, msg)


def raise_type_error(msg: str) -> None:
    """Raise a type error."""
    raise LuminaError(ErrorCategory.TYPE_ERROR, msg)


def raise_codegen_error(msg: str) -> None:
    """Raise a code generation error."""
    raise LuminaError(ErrorCategory.CODGEN_ERROR, msg)


def raise_runtime_error(msg: str) -> None:
    """Raise a runtime error."""
    raise LuminaError(ErrorCategory.RUNTIME_ERROR, msg)


def from_failure(msg: str) -> LuminaError:
    """Create an error from a failure message."""
    if msg.startswith("Parse error"):
        return LuminaError(ErrorCategory.PARSE_ERROR, msg)
    elif msg.startswith("Tokenization error"):
        return LuminaError(ErrorCategory.TOKENIZE_ERROR, msg)
    elif msg.startswith("Type error"):
        return LuminaError(ErrorCategory.TYPE_ERROR, msg)
    elif msg.startswith("Codegen error"):
        return LuminaError(ErrorCategory.CODGEN_ERROR, msg)
    else:
        return LuminaError(ErrorCategory.RUNTIME_ERROR, msg)