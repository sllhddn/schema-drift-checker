-- Export live column metadata in the CSV shape schema-drift expects.
-- psql -d mydb -c "\copy (<this query>) TO 'actual_columns.csv' CSV HEADER"
SELECT c.table_name,
       c.column_name,
       c.data_type,
       c.character_maximum_length AS char_length,
       CASE WHEN c.data_type = 'numeric' THEN c.numeric_precision END AS precision,
       CASE WHEN c.data_type = 'numeric' THEN c.numeric_scale END     AS scale,
       CASE c.is_nullable WHEN 'YES' THEN 'Y' ELSE 'N' END            AS nullable
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name AND t.table_type = 'BASE TABLE'
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;
