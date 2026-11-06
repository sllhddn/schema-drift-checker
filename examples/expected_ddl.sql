-- Expected schema, in the style of a Hibernate schema export (Oracle dialect).
-- All names are fictional.
create table land_parcel (
    id number(19,0) not null,
    lot_no varchar2(20 char) not null,
    district_code varchar2(10 char),
    area number(16,5),
    area_unit varchar2(5 char),
    registered_on date,
    remarks varchar2(4000 char),
    primary key (id)
);
create table application (
    id number(19,0) not null,
    parcel_id number(19,0),
    applicant_name varchar2(250 char) not null,
    status varchar2(20 char) not null,
    submitted_on timestamp,
    fee_amount number(12,2),
    notes clob,
    primary key (id),
    constraint fk_app_parcel foreign key (parcel_id) references land_parcel
);
create table payment (
    id number(19,0) not null,
    application_id number(19,0) not null,
    payer_name varchar2(250 char),
    amount number(12,2) not null,
    paid_on timestamp,
    receipt_no varchar2(30 char),
    primary key (id)
);
create table ref_status (
    code varchar2(20 char) not null,
    description varchar2(200 char),
    is_active char(1),
    primary key (code)
);
create table audit_log (
    id number(19,0) not null,
    entity varchar2(100 char),
    action varchar2(20 char),
    created_at timestamp,
    primary key (id)
);
