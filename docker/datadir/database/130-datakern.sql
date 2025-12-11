CREATE SCHEMA IF NOT EXISTS datakern;
CREATE SCHEMA IF NOT EXISTS data;

CREATE SEQUENCE datakern.hibernate_sequence;
GRANT ALL ON datakern.hibernate_sequence TO georchestra;

CREATE TYPE datakern.rule_type_enum AS ENUM
    (
        'DATA',
        'METADATA',
        'BOTH'
        );

CREATE TYPE datakern.rule_value_enum AS ENUM
    (
        'READ',
        'WRITE'
        );

create table if not exists datakern.integrity_link
(
    id                        uuid      DEFAULT gen_random_uuid() PRIMARY KEY,
    data_id                   varchar(256)       NULL,
    metadata_id               varchar(256)       NULL,
    integrity_title           text               NULL,
    integrity_owner           varchar(256)       NOT NULL,
    integrity_organization    varchar(256)       NOT NULL,
    integrity_transformation  jsonb              NULL,
    staging_table_name        varchar(63)        NULL,
    staging_retrieve_time     interval           NULL,
    final_table_name          varchar(63) UNIQUE NULL,
    last_retrieval_timestamp  timestamp           NULL,
    schedule                  varchar(10)        NULL,
    schedule_enabled          boolean   default false,
    created_at                timestamp default current_timestamp
);

comment on column datakern.integrity_link.staging_retrieve_time is
    'Estimated time taken to retrieve data into staging table. Used to define the minimum interval allowed between two schedules.';
comment on column datakern.integrity_link.last_retrieval_timestamp is
    'Timestamp of the last successful retrieval into the final table';

create table if not exists datakern.integrity_link_rules
(
    id                     serial,
    integrity_link_id      uuid REFERENCES datakern.integrity_link (id) ON DELETE CASCADE,
    rule_type              datakern.rule_type_enum  DEFAULT 'BOTH',
    rule_value             datakern.rule_value_enum DEFAULT 'READ',
    organization_concerned varchar(256) NULL
);
