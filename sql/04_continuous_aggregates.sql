-- Hourly metrics per device
CREATE MATERIALIZED VIEW IF NOT EXISTS device_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    device_id,
    AVG(cpu_usage)        AS avg_cpu_usage,
    MAX(cpu_usage)        AS max_cpu_usage,
    AVG(memory_usage)     AS avg_memory_usage,
    AVG(temperature)      AS avg_temperature,
    MAX(temperature)      AS max_temperature,
    COUNT(*)              AS sample_count,
    SUM(CASE WHEN error_code IS NOT NULL AND error_code != 0 THEN 1 ELSE 0 END) AS error_count
FROM device_metrics
GROUP BY bucket, device_id
WITH NO DATA;

-- Optional: automatic refresh policy (if you want to showcase policies)
SELECT add_continuous_aggregate_policy(
    'device_metrics_hourly',
    start_offset     => INTERVAL '3 days',
    end_offset       => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);