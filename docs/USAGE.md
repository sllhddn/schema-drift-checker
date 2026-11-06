# schema-drift-checker: How to use

This guide walks through a full drift check: export the live schema, compare it with the expected DDL, read the
report, and fix sequence drift.

## 1. Install

Python 3.10+ is required. The only runtime dependency is `openpyxl`.

```bash
git clone https://github.com/sllhddn/schema-drift-checker.git
cd schema-drift-checker
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
schema-drift --help
```

## 2. Get the expected schema (what the code wants)

Any file of `CREATE TABLE` statements works. Common sources:

- **Hibernate / JPA:** a schema export, for example with `hibernate.hbm2ddl.auto=create` against a scratch database,
  or the `SchemaExport` tool, written to a file such as `expected_ddl.sql`.
- **Flyway / Liquibase projects:** run migrations on an empty database and dump the DDL.
- **Hand-written baseline:** the DDL kept in the repository.

Oracle-style types (`varchar2(20 char)`, `number(19,0)`, `clob`) are fine even if the live database is PostgreSQL.

## 3. Export the live schema (what the database has)

Run the matching query from `sql/` and save the result as CSV with a header row.

PostgreSQL (`psql`):

```bash
psql -d mydb --csv -f sql/export_columns_postgres.sql -o actual_columns.csv     # psql 12 or newer
```

Or run `sql/export_columns_postgres.sql` in DBeaver / pgAdmin and export the grid as CSV.

Oracle: run `sql/export_columns_oracle.sql` in DBeaver or SQL Developer with `:schema_owner` bound, then export
as CSV.

Required columns: `table_name, column_name, data_type`. Optional: `char_length, precision, scale, nullable`.

## 4. Compare

```bash
schema-drift compare \
  --ddl expected_ddl.sql \
  --catalog actual_columns.csv \
  --out drift_report.xlsx \
  --fix-sql fix.sql \
  --dialect postgres            # or oracle, controls the fix script syntax
```

Console summary:

```
Compared 4 tables -> drift_report.xlsx
  missing tables: 1  undocumented tables: 1  junk: 2
  missing columns: 1  extra columns: 1
  mismatches: CRITICAL=0, HIGH=3, MEDIUM=1, LOW=0, INFO=13
  draft fix script -> fix.sql
STATUS: ACTION NEEDED
```

Exit codes: `0` clean, `2` action needed. Schedule it nightly and alert on `2`.

## 5. Read the report

| Sheet | Read it as | Typical action |
|---|---|---|
| KPI Summary | Overall health and counts | Share with the team lead |
| Expected-Only Tables | Code expects a table the DB lacks | Run the missing migration |
| DB-Only Tables | Table exists only in the DB | Document it or plan removal |
| Junk Tables | `_bak`, `tmp_`, date-stamped copies | Confirm the owner, archive, drop |
| Missing Columns | Entity field with no column | Add the column (see `fix.sql`) |
| Extra Columns | Column no entity uses | Confirm it is unused before dropping |
| Type Mismatches | Sorted CRITICAL first | Fix CRITICAL and HIGH before the next release |

Severity rules:

| Severity | Rule |
|---|---|
| CRITICAL | Different, incompatible type families (`varchar` vs `numeric`) |
| HIGH | DB column smaller than expected (length, integer digits or scale) |
| MEDIUM | Nullability differs, or compatible families (`varchar` vs `text`) |
| LOW | DB column larger than expected |
| INFO | Same after normalisation, spelled differently |

## 6. Review the fix script

`fix.sql` is a **draft**. It adds missing columns and widens HIGH-severity columns to the expected size. Before running:

1. Check the target table size. `ALTER … TYPE` can rewrite and lock a large PostgreSQL table.
2. Run it on staging first.
3. Lint it with [sql-patch-guard](https://github.com/sllhddn/sql-patch-guard).

## 7. Fix sequence drift

Symptom: `ORA-00001: unique constraint violated` (Oracle) or `duplicate key value violates unique constraint`
(PostgreSQL, SQLSTATE 23505) on inserts that never collided before.

1. Find drifted sequences.
   - PostgreSQL: the query returns the right columns, so save it straight to CSV:
     `psql -d mydb --csv -f sql/sequence_drift_postgres.sql -o sequence_states.csv`
   - Oracle: `sql/sequence_drift_oracle.sql` prints one line per drifted sequence through DBMS_OUTPUT.
     Paste those lines into a file under the header `sequence,table,last_value,max_id`.
2. Generate the resync script:

   ```bash
   schema-drift sequences --states sequence_states.csv --dialect oracle
   ```

   ```sql
   -- seq_application: last_number=49870, MAX(id) in application=50213
   ALTER SEQUENCE seq_application INCREMENT BY 354;
   SELECT seq_application.NEXTVAL FROM dual;
   ALTER SEQUENCE seq_application INCREMENT BY 1;
   ```

3. Run it in a quiet window. On Oracle, nobody else should insert into that table between the three statements.

The increment is a pre-computed literal (gap + a buffer of 10) because Oracle does not evaluate `50213 - 49870` in DDL.

## 8. Tested against

The export query, the comparison and the PostgreSQL sequence query and fix were run end to end against
PostgreSQL 16. The Oracle queries follow the same logic but have not been run against an Oracle instance in this repo's CI.

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every column shows as a mismatch | CSV lengths in bytes, DDL in characters | Export `char_length`, not `data_length` |
| A table shows as both missing and DB-only | Name differs in case or has a schema prefix | Names are compared in lower case; remove schema prefixes from the CSV |
| `KeyError: 'table_name'` | CSV header names differ | Rename headers to `table_name, column_name, data_type` |
| Constraint names appear as columns | Unusual constraint syntax | Put table constraints after columns, starting with `CONSTRAINT`, `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE` or `CHECK` |

## 10. Run the tests

```bash
pytest -q
```
