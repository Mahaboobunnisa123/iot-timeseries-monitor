-- Convert device_metrics into a hypertable partitioned on time
SELECT create_hypertable(
    'device_metrics',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);