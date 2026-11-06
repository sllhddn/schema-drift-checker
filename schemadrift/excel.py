"""Write a DriftReport to a styled Excel workbook."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .compare import SEVERITY_ORDER, DriftReport

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
BAND_FILL = PatternFill("solid", fgColor="F2F5FA")
SEV_FILL = {
    "CRITICAL": "F8CBAD", "HIGH": "FCE4D6", "MEDIUM": "FFF2CC", "LOW": "E2EFDA", "INFO": "EDEDED",
}
FONT = "Arial"


def _sheet(wb: Workbook, title: str, headers: list[str], rows: list[list], sev_col: int | None = None):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center")
    for i, row in enumerate(rows, start=2):
        ws.append(row)
        for cell in ws[i]:
            cell.font = Font(name=FONT, size=10)
            if i % 2 == 0:
                cell.fill = BAND_FILL
        if sev_col is not None:
            ws.cell(i, sev_col + 1).fill = PatternFill("solid", fgColor=SEV_FILL[row[sev_col]])
    for idx, h in enumerate(headers, start=1):
        width = max([len(str(h))] + [len(str(r[idx - 1])) for r in rows]) + 2
        ws.column_dimensions[get_column_letter(idx)].width = min(width, 70)
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions
    return ws


def write_report(report: DriftReport, path: Path, expected_label: str, actual_label: str) -> Path:
    wb = Workbook()
    wb.remove(wb.active)

    counts = report.severity_counts()
    kpis = [
        ["Expected source", expected_label],
        ["Actual source", actual_label],
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["Tables compared", report.tables_compared],
        ["Tables only in expected (missing in DB)", len(report.expected_only_tables)],
        ["Tables only in DB (undocumented)", len(report.actual_only_tables)],
        ["Junk / backup tables", len(report.junk_tables)],
        ["Missing columns", len(report.missing_columns)],
        ["Extra columns", len(report.extra_columns)],
    ] + [[f"Type mismatches - {s}", counts[s]] for s in SEVERITY_ORDER] + [
        ["Overall status", "CLEAN" if report.is_clean else "ACTION NEEDED"],
    ]
    _sheet(wb, "KPI Summary", ["Metric", "Value"], kpis)

    _sheet(wb, "Expected-Only Tables", ["Table"], [[t] for t in report.expected_only_tables])
    _sheet(wb, "DB-Only Tables", ["Table"], [[t] for t in report.actual_only_tables])
    _sheet(wb, "Junk Tables", ["Table", "Suggested action"],
           [[t, "Confirm owner, then archive / drop"] for t in report.junk_tables])
    _sheet(wb, "Missing Columns", ["Table", "Column", "Expected type", "Nullable"],
           [[t, c.name, c.describe(), "Y" if c.nullable else "N"] for t, c in report.missing_columns])
    _sheet(wb, "Extra Columns", ["Table", "Column", "DB type", "Nullable"],
           [[t, c.name, c.describe(), "Y" if c.nullable else "N"] for t, c in report.extra_columns])
    _sheet(wb, "Type Mismatches", ["Severity", "Table", "Column", "Expected", "Actual", "Reason"],
           [[m.severity, m.table, m.column, m.expected, m.actual, m.reason] for m in report.mismatches],
           sev_col=0)

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
