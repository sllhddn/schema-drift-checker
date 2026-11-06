"""Load an expected schema from DDL and an actual schema from a catalog export (CSV)."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from .model import Schema, Table, make_column

_CREATE = re.compile(r"create\s+table\s+(?:\w+\.)?\"?(\w+)\"?\s*\((.*)\)\s*$", re.I | re.S)
_CONSTRAINT_WORDS = ("primary key", "foreign key", "constraint", "unique", "check")


def _split_top_level(body: str) -> list[str]:
    """Split a column list on commas that are not inside parentheses."""
    parts, depth, cur = [], 0, []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def load_ddl(text: str) -> Schema:
    """Parse CREATE TABLE statements (e.g. Hibernate schema export) into a Schema."""
    text = re.sub(r"--[^\n]*", "", text)
    schema: Schema = {}
    for stmt in text.split(";"):
        m = _CREATE.search(stmt.strip())
        if not m:
            continue
        table = Table(m.group(1).lower())
        for part in _split_top_level(m.group(2)):
            if part.lower().startswith(_CONSTRAINT_WORDS):
                continue
            cm = re.match(r'"?(\w+)"?\s+(.+)$', part, re.S)
            if not cm:
                continue
            name, rest = cm.group(1), " ".join(cm.group(2).split())
            # type ends where a column option starts
            tm = re.match(r"(.+?)(?=\s+(?:not\s+null|null|default|primary|unique|references|check|constraint)\b|$)",
                          rest, re.I)
            raw_type = tm.group(1) if tm else rest
            nullable = not re.search(r"\bnot\s+null\b|\bprimary\s+key\b", rest, re.I)
            table.columns[name.lower()] = make_column(name, raw_type, nullable)
        schema[table.name] = table
    return schema


def load_catalog_csv(path: Path) -> Schema:
    """Load an information_schema / ALL_TAB_COLUMNS export.

    Expected headers (case-insensitive): table_name, column_name, data_type,
    and optionally char_length, precision, scale, nullable (Y/N or YES/NO).
    """
    schema: Schema = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
            t = row["table_name"].lower()
            raw = row["data_type"]
            if row.get("char_length"):
                raw = f"{raw}({row['char_length']})"
            elif row.get("precision"):
                raw = f"{raw}({row['precision']},{row.get('scale') or 0})"
            nullable = row.get("nullable", "Y").upper() in ("Y", "YES", "TRUE", "1")
            schema.setdefault(t, Table(t)).columns[row["column_name"].lower()] = \
                make_column(row["column_name"], raw, nullable)
    return schema
