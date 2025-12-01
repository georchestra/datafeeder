CREATE SCHEMA datakern;

CREATE SEQUENCE datakern.hibernate_sequence;
GRANT ALL ON datakern.hibernate_sequence TO georchestra;

create table if not exists datakern.integrity_link
(
    id                       uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    data_id                  varchar(256) NULL,
    metadata_id              varchar(256) NULL,
    integrity_owner          varchar(256) NOT NULL ,
    integrity_organization   text NOT NULL ,
    integrity_transformation jsonb NULL,
    staging_table_name       varchar(63) NULL ,
    last_staging_retrieved_at timestamp NULL,
    final_table_name         varchar(63) UNIQUE NULL,
    retrieve_time           interval NULL,
--     integrity_status         varchar(50)  NULL,
    schedule                 varchar(10)  NULL,
    schedule_enabled         boolean  default false,
    created_at               timestamp default current_timestamp
);

create table if not exists datakern.staging_job
(
    id                 serial,
    dag_run_id         varchar(256),
    status             varchar(50)  default 'QUEUED',
    created_at         timestamp default current_timestamp
);

