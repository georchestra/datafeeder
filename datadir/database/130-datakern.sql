CREATE SCHEMA datakern;

CREATE SEQUENCE datakern.hibernate_sequence;
GRANT ALL ON datakern.hibernate_sequence TO georchestra;

create table if not exists datakern.integrity_link
(
    id                       serial,
    data_id                  varchar(256) NULL,
    metadata_id              varchar(256) NULL,
    integrity_owner          text,
    integrity_organization   text,
    integrity_transformation jsonb,
    staging_table_name       varchar(256),
    final_table_name         varchar(256),
--     integrity_status         varchar(50)  NULL,
    schedule                 varchar(10)  NULL,
    schedule_enabled         boolean   default true,
    created_at               timestamp default current_timestamp
);

create table if not exists datakern.staging_job
(
    id                 serial,
    dag_run_id         varchar(256),
    staging_table_name varchar(256),
    created_at         timestamp default current_timestamp
);

