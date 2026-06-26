"""Type definitions for the Lumina language."""

from dataclasses import dataclass
from typing import List, Tuple, Optional


class Typ:
    """Base class for types."""
    def __eq__(self, other):
        return isinstance(other, self.__class__)
    
    def __hash__(self):
        return hash(self.__class__.__name__)


class TNum(Typ):
    """Numeric type."""
    def __repr__(self):
        return "Num"
    
    def __eq__(self, other):
        return isinstance(other, TNum)
    
    def __hash__(self):
        return hash("TNum")


class TBool(Typ):
    """Boolean type."""
    def __repr__(self):
        return "Bool"
    
    def __eq__(self, other):
        return isinstance(other, TBool)
    
    def __hash__(self):
        return hash("TBool")


class TStr(Typ):
    """String type."""
    def __repr__(self):
        return "Str"
    
    def __eq__(self, other):
        return isinstance(other, TStr)
    
    def __hash__(self):
        return hash("TStr")


class TColor(Typ):
    """Color type."""
    def __repr__(self):
        return "Color"
    
    def __eq__(self, other):
        return isinstance(other, TColor)
    
    def __hash__(self):
        return hash("TColor")


class TTime(Typ):
    """Time type."""
    def __repr__(self):
        return "Time"
    
    def __eq__(self, other):
        return isinstance(other, TTime)
    
    def __hash__(self):
        return hash("TTime")


@dataclass
class TTuple(Typ):
    """Tuple type."""
    elements: List[Typ]
    
    def __repr__(self):
        return f"Tuple({self.elements})"
    
    def __eq__(self, other):
        if not isinstance(other, TTuple):
            return False
        if len(self.elements) != len(other.elements):
            return False
        return all(a == b for a, b in zip(self.elements, other.elements))
    
    def __hash__(self):
        return hash(("TTuple", tuple(self.elements)))


@dataclass
class TArray(Typ):
    """Array type."""
    element_type: Typ
    
    def __repr__(self):
        return f"Array({self.element_type})"
    
    def __eq__(self, other):
        if not isinstance(other, TArray):
            return False
        return self.element_type == other.element_type
    
    def __hash__(self):
        return hash(("TArray", self.element_type))


@dataclass
class TStruct(Typ):
    """Structure type."""
    name: str
    fields: List[Tuple[str, Typ]]
    
    def __repr__(self):
        return f"Struct({self.name}, {self.fields})"
    
    def __eq__(self, other):
        if not isinstance(other, TStruct):
            return False
        if self.name != other.name:
            return False
        if len(self.fields) != len(other.fields):
            return False
        return all((n1 == n2 and t1 == t2) for (n1, t1), (n2, t2) in zip(self.fields, other.fields))
    
    def __hash__(self):
        return hash(("TStruct", self.name, tuple(self.fields)))


@dataclass
class TFn(Typ):
    """Function type."""
    arity: int
    
    def __repr__(self):
        return f"Fn/{self.arity}"
    
    def __eq__(self, other):
        if not isinstance(other, TFn):
            return False
        return self.arity == other.arity
    
    def __hash__(self):
        return hash(("TFn", self.arity))


class TVoid(Typ):
    """Void type."""
    def __repr__(self):
        return "Void"
    
    def __eq__(self, other):
        return isinstance(other, TVoid)
    
    def __hash__(self):
        return hash("TVoid")


class TAny(Typ):
    """Any type."""
    def __repr__(self):
        return "Any"
    
    def __eq__(self, other):
        return isinstance(other, TAny)
    
    def __hash__(self):
        return hash("TAny")


class TShape(Typ):
    """Shape type."""
    def __repr__(self):
        return "Shape"
    
    def __eq__(self, other):
        return isinstance(other, TShape)
    
    def __hash__(self):
        return hash("TShape")


def pp_typ(t: Typ) -> str:
    """Pretty print a type."""
    if isinstance(t, TNum):
        return "Num"
    elif isinstance(t, TBool):
        return "Bool"
    elif isinstance(t, TStr):
        return "Str"
    elif isinstance(t, TColor):
        return "Color"
    elif isinstance(t, TTime):
        return "Time"
    elif isinstance(t, TTuple):
        return f"Tuple({', '.join(pp_typ(e) for e in t.elements)})"
    elif isinstance(t, TArray):
        return f"Array({pp_typ(t.element_type)})"
    elif isinstance(t, TStruct):
        return f"Struct({t.name})"
    elif isinstance(t, TFn):
        return f"Fn/{t.arity}"
    elif isinstance(t, TVoid):
        return "Void"
    elif isinstance(t, TAny):
        return "Any"
    elif isinstance(t, TShape):
        return "Shape"
    else:
        return "Unknown"