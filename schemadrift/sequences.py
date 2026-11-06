"""Detect sequence drift and generate a safe resync script.

Sequence drift = the sequence's next value is at or below MAX(id) of the table
it feeds, so the next INSERT hits a primary key violation (ORA-00001 /
PostgreSQL 23505).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SequenceState:
    sequence: str
    table: str
    last_value: int   # Oracle: dba_sequences.last_number / PG: pg_sequences.last_value
    max_id: int       # SELECT MAX(id) FROM table

    @property
    def drifted(self) -> bool:
        return self.last_value <= self.max_id

    @property
    def gap(self) -> int:
        return self.max_id - self.last_value + 1


def load_states(path: Path) -> list[SequenceState]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [SequenceState(r["sequence"], r["table"], int(r["last_value"]), int(r["max_id"]))
                for r in csv.DictReader(fh)]


def oracle_fix(s: SequenceState, buffer: int = 10) -> str:
    """Three-step Oracle resync. The gap is a pre-computed literal - Oracle DDL does not evaluate expressions."""
    step = s.gap + buffer
    return (f"-- {s.sequence}: last_number={s.last_value}, MAX(id) in {s.table}={s.max_id}\n"
            f"ALTER SEQUENCE {s.sequence} INCREMENT BY {step};\n"
            f"SELECT {s.sequence}.NEXTVAL FROM dual;\n"
            f"ALTER SEQUENCE {s.sequence} INCREMENT BY 1;\n")


def postgres_fix(s: SequenceState) -> str:
    return (f"-- {s.sequence}: last_value={s.last_value}, MAX(id) in {s.table}={s.max_id}\n"
            f"SELECT setval('{s.sequence}', (SELECT MAX(id) FROM {s.table}));\n")


def build_script(states: list[SequenceState], dialect: str) -> str:
    drifted = [s for s in states if s.drifted]
    head = f"-- {len(drifted)} of {len(states)} sequences need a resync ({dialect})\n"
    body = "\n".join(oracle_fix(s) if dialect == "oracle" else postgres_fix(s) for s in drifted)
    return head + ("\n" + body if body else "-- nothing to do\n")
