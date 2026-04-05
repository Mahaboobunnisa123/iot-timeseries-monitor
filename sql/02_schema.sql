-- Device metadata (dimension table)
CREATE TABLE IF NOT EXISTS devices (
    device_id      SERIAL PRIMARY KEY,
    device_name    TEXT NOT NULL,
    device_type    TEXT NOT NULL,
    location       TEXT NOT NULL,
    installed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Raw telemetry (fact table; will become hypertable)
CREATE TABLE IF NOT EXISTS device_metrics (
    time          TIMESTAMPTZ NOT NULL,
    device_id     INT NOT NULL REFERENCES devices(device_id),
    cpu_usage     DOUBLE PRECISION NOT NULL,  -- percentage 0–100
    memory_usage  DOUBLE PRECISION NOT NULL,  -- MB
    temperature   DOUBLE PRECISION NOT NULL,  -- Celsius
    error_code    INT,                        -- nullable; 0 = OK, non-zero = error
    status        TEXT NOT NULL DEFAULT 'OK'  -- e.g. OK, DEGRADED, DOWN
);