"""schema-drift CLI.

  schema-drift compare --ddl expected.sql --catalog actual.csv --out report.xlsx [--fix-sql fix.sql]
  schema-drift sequences --states seq_states.csv --dialect oracle
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compare import compare, fix_sql
from .excel import write_report
from .loaders import load_catalog_csv, load_ddl
from .sequences import build_script, load_states


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="schema-drift")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare", help="compare expected DDL against a live catalog export")
    c.add_argument("--ddl", type=Path, required=True, help="expected schema as CREATE TABLE statements")
    c.add_argument("--catalog", type=Path, required=True, help="CSV export of the live schema's columns")
    c.add_argument("--out", type=Path, default=Path("drift_report.xlsx"))
    c.add_argument("--fix-sql", type=Path, help="also write a draft remediation script")
    c.add_argument("--dialect", choices=["postgres", "oracle"], default="postgres")

    s = sub.add_parser("sequences", help="generate a resync script for drifted sequences")
    s.add_argument("--states", type=Path, required=True, help="CSV: sequence,table,last_value,max_id")
    s.add_argument("--dialect", choices=["postgres", "oracle"], default="oracle")

    args = p.parse_args(argv)

    if args.cmd == "sequences":
        print(build_script(load_states(args.states), args.dialect))
        return 0

    report = compare(load_ddl(args.ddl.read_text(encoding="utf-8")), load_catalog_csv(args.catalog))
    write_report(report, args.out, args.ddl.name, args.catalog.name)
    counts = report.severity_counts()
    print(f"Compared {report.tables_compared} tables -> {args.out}")
    print(f"  missing tables: {len(report.expected_only_tables)}  undocumented tables: "
          f"{len(report.actual_only_tables)}  junk: {len(report.junk_tables)}")
    print(f"  missing columns: {len(report.missing_columns)}  extra columns: {len(report.extra_columns)}")
    print("  mismatches: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    if args.fix_sql:
        args.fix_sql.write_text(fix_sql(report, args.dialect), encoding="utf-8")
        print(f"  draft fix script -> {args.fix_sql}")
    print("STATUS:", "CLEAN" if report.is_clean else "ACTION NEEDED")
    return 0 if report.is_clean else 2


if __name__ == "__main__":
    sys.exit(main())
