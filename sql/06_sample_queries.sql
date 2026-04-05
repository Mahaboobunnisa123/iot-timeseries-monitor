-- IoT Timeseries Monitor - Sample Analytical Queries

-- QUERY 1: Last 1 hour of metrics for a specific device
SELECT
    dm.time,
    d.device_name,
    dm.cpu_usage,
    dm.memory_usage,
    dm.temperature,
    dm.status
FROM device_metrics dm
JOIN devices d ON dm.device_id = d.device_id
WHERE d.device_name = 'device-001'
  AND dm.time >= NOW() - INTERVAL '1 hour'
ORDER BY dm.time DESC
LIMIT 10;

-- QUERY 2: Top 5 devices with highest temperature (last 24h)
SELECT
    d.device_name,
    MAX(dm.temperature) AS max_temp
FROM device_metrics dm
JOIN devices d ON dm.device_id = d.device_id
WHERE dm.time >= NOW() - INTERVAL '24 hours'
GROUP BY d.device_name
ORDER BY max_temp DESC
LIMIT 5;

-- QUERY 3: Error rate per device (last 24 hours)
SELECT
    d.device_name,
    COUNT(*) FILTER (WHERE dm.error_code IS NOT NULL AND dm.error_code != 0) AS errors,
    COUNT(*) AS total,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE dm.error_code IS NOT NULL AND dm.error_code != 0)
        / NULLIF(COUNT(*), 0),
        2
    ) AS error_rate_pct
FROM device_metrics dm
JOIN devices d ON dm.device_id = d.device_id
WHERE dm.time >= NOW() - INTERVAL '24 hours'
GROUP BY d.device_name
ORDER BY error_rate_pct DESC NULLS LAST;

-- QUERY 4: Hourly stats using continuous aggregate (last 24h)
\SELECT
    bucket,
    d.device_name,
    avg_cpu_usage,
    max_cpu_usage,
    avg_memory_usage,
    avg_temperature,
    error_count,
    sample_count
FROM device_metrics_hourly h
JOIN devices d ON h.device_id = d.device_id
WHERE bucket >= NOW() - INTERVAL '24 hours'
ORDER BY bucket DESC, d.device_name
LIMIT 10;

-- QUERY 5: EXPLAIN ANALYZE - Raw hypertable aggregation (7 days)
-- Shows: Seq Scan on chunks, Execution Time ~15ms
EXPLAIN ANALYZE
SELECT
    time_bucket('1 hour', time) AS bucket,
    AVG(cpu_usage) AS avg_cpu
FROM device_metrics
WHERE time >= NOW() - INTERVAL '7 days'
GROUP BY bucket
ORDER BY bucket;

-- QUERY 6: EXPLAIN ANALYZE - Continuous aggregate (7 days)
-- Shows: Index Scan on materialized data, Execution Time ~1.7ms (~9x faster)
EXPLAIN ANALYZE
SELECT
    bucket,
    AVG(avg_cpu_usage) AS avg_cpu
FROM device_metrics_hourly
WHERE bucket >= NOW() - INTERVAL '7 days'
GROUP BY bucket
ORDER BY bucket;

-- QUERY 7: Transaction & Data Integrity Demo
-- FK constraint prevents orphan telemetry (device_id 99999 not in devices)
BEGIN;
INSERT INTO devices (device_name, device_type, location)
VALUES ('device-tx-test', 'sensor', 'lab');

-- This will fail: device_id 99999 does not exist in devices table
INSERT INTO device_metrics (time, device_id, cpu_usage, memory_usage, temperature, error_code, status)
VALUES (NOW(), 99999, 50.0, 512.0, 30.0, NULL, 'OK');

ROLLBACK;

-- Verify nothing was committed (should return 0 rows)
SELECT * FROM devices WHERE device_name = 'device-tx-test';