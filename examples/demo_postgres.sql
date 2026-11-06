-- Fictional "live" database with deliberate drift, used by CI and the usage guide.
-- psql -d demo -f examples/demo_postgres.sql
CREATE TABLE land_parcel (id bigserial PRIMARY KEY, lot_no varchar(20) NOT NULL, district_code varchar(10),
    area numeric(16,4), area_unit varchar(5), registered_on timestamp, remarks varchar(1000), legacy_ref varchar(50));
CREATE TABLE application (id bigserial PRIMARY KEY, parcel_id bigint, applicant_name varchar(250) NOT NULL,
    status varchar(20), submitted_on timestamp, fee_amount numeric(12,2), notes text);
CREATE TABLE payment (id bigserial PRIMARY KEY, application_id bigint NOT NULL, payer_name varchar(100),
    amount numeric(12,2) NOT NULL, paid_on timestamp);
CREATE TABLE ref_status (code varchar(20) PRIMARY KEY, description varchar(200), is_active char(1));
CREATE TABLE payment_bak_20240115 (id bigint NOT NULL, amount numeric(12,2));

-- 50 rows, then pull the sequence back to 20 to simulate sequence drift
INSERT INTO application (applicant_name) SELECT 'applicant ' || g FROM generate_series(1, 50) g;
SELECT setval('application_id_seq', 20);
