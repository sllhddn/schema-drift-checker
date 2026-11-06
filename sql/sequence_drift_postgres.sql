-- Sequences that would hand out an id that already exists in the column they feed.
-- Output columns match what `schema-drift sequences --states` expects, so you can save it straight to CSV:
--   psql -d mydb --csv -f sql/sequence_drift_postgres.sql -o sequence_states.csv
WITH owned AS (
    SELECT s.sequencename                     AS sequence,
           d.refobjid::regclass::text         AS "table",
           a.attname                          AS col,
           COALESCE(s.last_value, 0)          AS last_value
    FROM pg_sequences s
    JOIN pg_class c      ON c.relname = s.sequencename
    JOIN pg_namespace n  ON n.oid = c.relnamespace AND n.nspname = s.schemaname
    JOIN pg_depend d     ON d.objid = c.oid AND d.deptype IN ('a', 'i')
    JOIN pg_attribute a  ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
),
with_max AS (
    SELECT o.*,
           COALESCE((xpath('/row/m/text()',
                    query_to_xml(format('SELECT MAX(%I) AS m FROM %s', o.col, o."table"), false, true, '')))[1]::text::bigint, 0) AS max_id
    FROM owned o
)
SELECT sequence, "table", last_value, max_id
FROM with_max
WHERE max_id > 0 AND last_value < max_id      -- nextval() = last_value + 1 would collide
ORDER BY "table";
