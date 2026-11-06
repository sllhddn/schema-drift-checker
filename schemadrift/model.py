"""Common column model + type normalisation between Oracle and PostgreSQL."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Column:
    name: str
    type: str                      # normalised base type, e.g. "varchar", "numeric", "timestamp"
    length: int | None = None      # character length
    precision: int | None = None   # numeric precision
    scale: int | None = None       # numeric scale
    nullable: bool = True
    raw_type: str = ""             # type as written in the source, for the report

    def describe(self) -> str:
        if self.length:
            return f"{self.type}({self.length})"
        if self.precision is not None:
            return f"{self.type}({self.precision},{self.scale or 0})"
        return self.type


@dataclass
class Table:
    name: str
    columns: dict[str, Column] = field(default_factory=dict)


Schema = dict[str, Table]

# Oracle (as produced by Hibernate's Oracle dialect) and PostgreSQL spellings -> one canonical family
_TYPE_MAP = {
    "varchar2": "varchar", "nvarchar2": "varchar", "varchar": "varchar", "character varying": "varchar",
    "char": "char", "character": "char", "bpchar": "char", "nchar": "char",
    "number": "numeric", "numeric": "numeric", "decimal": "numeric",
    "integer": "integer", "int": "integer", "int4": "integer", "smallint": "integer", "int2": "integer",
    "bigint": "integer", "int8": "integer",
    "float": "float", "double precision": "float", "real": "float", "binary_double": "float", "float8": "float",
    "date": "timestamp", "timestamp": "timestamp", "timestamp without time zone": "timestamp",
    "timestamp with time zone": "timestamptz", "timestamptz": "timestamptz",
    "clob": "text", "nclob": "text", "long": "text", "text": "text",
    "blob": "binary", "raw": "binary", "long raw": "binary", "bytea": "binary",
    "boolean": "boolean", "bool": "boolean",
}

# Families that can hold each other's values without conversion (for severity grading)
COMPATIBLE = {
    frozenset({"numeric", "integer"}),
    frozenset({"varchar", "text"}),
    frozenset({"char", "varchar"}),
    frozenset({"timestamp", "timestamptz"}),
}


def normalise_type(raw: str) -> tuple[str, int | None, int | None, int | None]:
    """Return (family, length, precision, scale) for a raw SQL type string."""
    raw = raw.strip().lower()
    m = re.match(r"^([a-z][a-z0-9_ ]*?)\s*(?:\(\s*(\d+)\s*(?:char|byte)?\s*(?:,\s*(-?\d+))?\s*\))?\s*$", raw)
    if not m:
        return raw, None, None, None
    base, a, b = m.group(1).strip(), m.group(2), m.group(3)
    family = _TYPE_MAP.get(base, base)
    a = int(a) if a else None
    b = int(b) if b else None
    if family in ("varchar", "char"):
        return family, a, None, None
    if family == "numeric":
        # Oracle NUMBER(10,0) is an integer in disguise
        if a is not None and (b in (None, 0)) and base in ("number",):
            return "integer", None, a, 0
        return family, None, a, b if b is not None else (0 if a is not None else None)
    if family == "integer":
        return family, None, None, None
    return family, None, None, None


def make_column(name: str, raw_type: str, nullable: bool = True) -> Column:
    fam, length, prec, scale = normalise_type(raw_type)
    return Column(name.lower(), fam, length, prec, scale, nullable, raw_type.strip())
