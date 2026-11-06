-- Find sequences whose next value would collide with existing primary keys.
-- Assumes the naming convention SEQ_<TABLE> -> <TABLE>.ID ; adjust the mapping for your schema.
SET SERVEROUTPUT ON   -- SQL*Plus / SQL Developer. In DBeaver remove this line and enable the Output panel instead.
DECLARE
  v_max NUMBER;
BEGIN
  FOR s IN (SELECT sequence_name, last_number
              FROM user_sequences
             WHERE sequence_name LIKE 'SEQ\_%' ESCAPE '\') LOOP
    BEGIN
      EXECUTE IMMEDIATE 'SELECT NVL(MAX(id),0) FROM ' || SUBSTR(s.sequence_name, 5) INTO v_max;
      IF s.last_number <= v_max THEN
        DBMS_OUTPUT.PUT_LINE(s.sequence_name || ',' || SUBSTR(s.sequence_name, 5) || ','
                             || s.last_number || ',' || v_max);
      END IF;
    EXCEPTION WHEN OTHERS THEN NULL;  -- table missing or no ID column
    END;
  END LOOP;
END;
/
