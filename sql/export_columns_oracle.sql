-- Export live column metadata from Oracle in the CSV shape schema-drift expects.
-- Run in DBeaver / SQL Developer and export the result grid as CSV.
SELECT LOWER(table_name)  AS table_name,
       LOWER(column_name) AS column_name,
       LOWER(data_type)   AS data_type,
       CASE WHEN data_type IN ('VARCHAR2','NVARCHAR2','CHAR','NCHAR') THEN char_length END AS char_length,
       CASE WHEN data_type = 'NUMBER' THEN data_precision END AS precision,
       CASE WHEN data_type = 'NUMBER' THEN data_scale END     AS scale,
       nullable
FROM all_tab_columns
WHERE owner = UPPER(:schema_owner)
ORDER BY table_name, column_id;
