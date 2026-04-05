-- Time + device index for most queries (filter by device and time window)
CREATE INDEX IF NOT EXISTS idx_device_metrics_device_time
    ON device_metrics (device_id, time DESC);

-- Time-only index for global time-range queries
CREATE INDEX IF NOT EXISTS idx_device_metrics_time
    ON device_metrics (time DESC);

-- Optional: index on (status, time) to filter "problem" devices quickly
CREATE INDEX IF NOT EXISTS idx_device_metrics_status_time
    ON device_metrics (status, time DESC);