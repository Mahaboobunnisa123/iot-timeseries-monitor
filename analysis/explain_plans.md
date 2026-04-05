# Query Execution Plans — IoT Timeseries Monitor

This file documents EXPLAIN ANALYZE outputs for key queries,
demonstrating PostgreSQL + TimescaleDB query optimization behavior.

## 1. Top 5 Hottest Devices (Last 24 Hours)

### Query
```sql
EXPLAIN ANALYZE
SELECT
    d.device_name,
    MAX(dm.temperature) AS max_temp
FROM device_metrics dm
JOIN devices d ON dm.device_id = d.device_id
WHERE dm.time >= NOW() - INTERVAL '24 hours'
GROUP BY d.device_name
ORDER BY max_temp DESC
LIMIT 5;
```
### Execution Plan
Limit (cost=627.71..627.72 rows=5 width=40) (actual time=9.067..9.072 rows=5 loops=1)
-> Sort (cost=627.71..628.21 rows=200 width=40) (actual time=9.066..9.070 rows=5 loops=1)
Sort Key: (max(dm.temperature)) DESC
Sort Method: top-N heapsort Memory: 25kB
-> HashAggregate (cost=622.39..624.39 rows=200 width=40) (actual time=8.826..8.835 rows=50 loops=1)
Group Key: d.device_name
-> Hash Join (cost=23.79..551.25 rows=14227 width=40) (actual time=0.272..7.150 rows=14200 loops=1)
Hash Cond: (dm.device_id = d.device_id)
-> Custom Scan (ChunkAppend) on device_metrics dm
-> Index Scan using _hyper_1_3_chunk_device_metrics_time_idx
Planning Time: 6.662 ms
Execution Time: 9.245 ms


### Observations
- `Custom Scan (ChunkAppend)` confirms TimescaleDB hypertable chunking is active
- `Index Scan` on time index — no full sequential scan
- Only recent chunks scanned — chunk pruning working correctly
- Processed 14,200 rows across 50 devices in 9.245ms


## 2. Raw Hypertable Aggregation vs Continuous Aggregate (7 Days)
### 2a. Raw Hypertable Query
```sql
EXPLAIN ANALYZE
SELECT
    time_bucket('1 hour', time) AS bucket,
    AVG(cpu_usage) AS avg_cpu
FROM device_metrics
WHERE time >= NOW() - INTERVAL '7 days'
GROUP BY bucket
ORDER BY bucket;
```
### Execution Plan — Raw Hypertable
Sort (cost=1509.64..1510.14 rows=200 width=16) (actual time=15.187..15.191 rows=73 loops=1)
-> Finalize HashAggregate (actual time=15.115..15.123 rows=73 loops=1)
-> Custom Scan (ChunkAppend) on device_metrics
-> Partial HashAggregate on _hyper_1_1_chunk
-> Seq Scan on _hyper_1_1_chunk rows=7900
-> Partial HashAggregate on _hyper_1_2_chunk
-> Seq Scan on _hyper_1_2_chunk rows=14400
-> Partial HashAggregate on _hyper_1_3_chunk
-> Seq Scan on _hyper_1_3_chunk rows=14400
-> Partial HashAggregate on _hyper_1_4_chunk
-> Seq Scan on _hyper_1_4_chunk rows=6500
Planning Time: 6.723 ms
Execution Time: 15.647 ms

### 2b. Continuous Aggregate Query
```sql
EXPLAIN ANALYZE
SELECT
    bucket,
    AVG(avg_cpu_usage) AS avg_cpu
FROM device_metrics_hourly
WHERE bucket >= NOW() - INTERVAL '7 days'
GROUP BY bucket
ORDER BY bucket;
```
### Execution Plan — Continuous Aggregate
GroupAggregate (cost=0.28..147.27 rows=200 width=16) (actual time=0.079..1.722 rows=73 loops=1)
-> Custom Scan (ChunkAppend) on _materialized_hypertable_2
-> Index Scan Backward using hyper_2_5_chunk_materialized_hypertable_2_bucket_idx
Index Cond: (bucket >= (now() - '7 days'::interval))
Planning Time: 3.886 ms
Execution Time: 1.783 ms

### Performance Comparison

| Metric | Raw Hypertable | Continuous Aggregate |
|---|---|---|
| Scan Type | Seq Scan (4 chunks) | Index Scan (materialized) |
| Rows Scanned | ~43,200 raw rows | 3,650 pre-aggregated rows |
| Execution Time | 15.647 ms | 1.783 ms |
| Speed Improvement | — | **~9x faster** |

### Observations
- Raw query does `Seq Scan` across 4 chunks scanning 43,200 rows
- Continuous aggregate uses `Index Scan` on pre-aggregated materialized data
- **~9x performance improvement** with continuous aggregate
- This is the core value of TimescaleDB continuous aggregates for analytics workloads

## 3. Transaction & Data Integrity Demo

### Query
```sql
BEGIN;
INSERT INTO devices (device_name, device_type, location)
VALUES ('device-tx-test', 'sensor', 'lab');

-- Intentional FK violation
INSERT INTO device_metrics (time, device_id, cpu_usage, memory_usage, temperature, error_code, status)
VALUES (NOW(), 99999, 50.0, 512.0, 30.0, NULL, 'OK');

ROLLBACK;
```

### Output
BEGIN
INSERT 0 1
ERROR: insert or update on table "_hyper_1_4_chunk" violates foreign key constraint
DETAIL: Key (device_id)=(99999) is not present in table "devices".
ROLLBACK

### Verification
```sql
SELECT * FROM devices WHERE device_name = 'device-tx-test';
-- Returns: (0 rows)
```

### Observations
- Foreign key constraint on `device_metrics.device_id` correctly rejected orphan telemetry
- PostgreSQL FK constraints work seamlessly on TimescaleDB hypertables
- Transaction rollback confirmed — no partial data committed
- This ensures data integrity: telemetry cannot exist without a valid device record
