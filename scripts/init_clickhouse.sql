CREATE DATABASE IF NOT EXISTS agentops;

CREATE TABLE IF NOT EXISTS agentops.spans
(
    trace_id String,
    span_id String,
    parent_span_id Nullable(String),
    agent_id String,
    agent_name String,
    run_id String,
    framework LowCardinality(String),
    span_type LowCardinality(String),
    start_time DateTime64(3, 'UTC'),
    end_time DateTime64(3, 'UTC'),
    duration_ms UInt32,
    status LowCardinality(String),
    error_message Nullable(String),
    attributes String,
    input_preview String,
    output_preview String,
    org_id String,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (org_id, run_id, start_time)
PARTITION BY toYYYYMM(start_time);
