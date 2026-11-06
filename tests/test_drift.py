from pathlib import Path

from openpyxl import load_workbook

from schemadrift.cli import main
from schemadrift.compare import compare, fix_sql, is_junk
from schemadrift.loaders import load_catalog_csv, load_ddl
from schemadrift.model import normalise_type
from schemadrift.sequences import SequenceState, build_script, oracle_fix

EX = Path(__file__).parent.parent / "examples"


def test_type_normalisation():
    assert normalise_type("varchar2(20 char)") == ("varchar", 20, None, None)
    assert normalise_type("character varying(20)") == ("varchar", 20, None, None)
    assert normalise_type("number(19,0)") == ("integer", None, 19, 0)
    assert normalise_type("bigint")[0] == "integer"
    assert normalise_type("number(16,5)") == ("numeric", None, 16, 5)
    assert normalise_type("clob")[0] == normalise_type("text")[0] == "text"
    assert normalise_type("date")[0] == "timestamp"


def test_ddl_parser_skips_constraints():
    s = load_ddl((EX / "expected_ddl.sql").read_text())
    assert set(s) == {"land_parcel", "application", "payment", "ref_status", "audit_log"}
    assert "fk_app_parcel" not in s["application"].columns
    assert s["application"].columns["applicant_name"].nullable is False
    assert s["land_parcel"].columns["area"].describe() == "numeric(16,5)"


def test_junk_detection():
    assert is_junk("payment_bak_20240115")
    assert is_junk("tmp_import_parcels")
    assert not is_junk("survey_request")


def report():
    return compare(load_ddl((EX / "expected_ddl.sql").read_text()), load_catalog_csv(EX / "actual_columns.csv"))


def test_compare_finds_expected_drift():
    r = report()
    assert r.expected_only_tables == ["audit_log"]
    assert r.actual_only_tables == ["survey_request"]
    assert set(r.junk_tables) == {"payment_bak_20240115", "tmp_import_parcels"}
    assert [(t, c.name) for t, c in r.extra_columns] == [("land_parcel", "legacy_ref")]
    by_col = {(m.table, m.column): m.severity for m in r.mismatches}
    assert by_col[("land_parcel", "area")] == "HIGH"          # numeric(16,4) vs (16,5)
    assert by_col[("land_parcel", "remarks")] == "HIGH"       # 1000 < 4000
    assert by_col[("payment", "payer_name")] == "HIGH"        # 100 < 250
    assert by_col[("application", "status")] == "MEDIUM"      # nullability
    assert ("land_parcel", "id") not in by_col                # number(19,0) == bigint
    assert not r.is_clean


def test_fix_sql_is_draft_and_dialect_aware():
    pg = fix_sql(report(), "postgres")
    ora = fix_sql(report(), "oracle")
    assert "REVIEW BEFORE RUNNING" in pg
    assert "ALTER TABLE land_parcel ALTER COLUMN remarks TYPE varchar(4000);" in pg
    assert "ALTER TABLE land_parcel MODIFY (remarks varchar2(4000));" in ora


def test_excel_report(tmp_path):
    out = tmp_path / "r.xlsx"
    rc = main(["compare", "--ddl", str(EX / "expected_ddl.sql"), "--catalog", str(EX / "actual_columns.csv"),
               "--out", str(out), "--fix-sql", str(tmp_path / "fix.sql")])
    assert rc == 2
    wb = load_workbook(out)
    assert wb.sheetnames == ["KPI Summary", "Expected-Only Tables", "DB-Only Tables", "Junk Tables",
                             "Missing Columns", "Extra Columns", "Type Mismatches"]
    assert wb["Type Mismatches"]["A2"].value == "HIGH"
    assert (tmp_path / "fix.sql").exists()


def test_sequence_fix_uses_literal():
    s = SequenceState("seq_application", "application", 49870, 50213)
    assert s.drifted and s.gap == 344
    sql = oracle_fix(s)
    assert "INCREMENT BY 354;" in sql and sql.strip().endswith("INCREMENT BY 1;")


def test_sequence_script_only_includes_drifted():
    from schemadrift.sequences import load_states
    script = build_script(load_states(EX / "sequence_states.csv"), "postgres")
    assert script.startswith("-- 2 of 4")
    assert "seq_application" in script and "seq_payment" in script
    assert "seq_land_parcel" not in script
