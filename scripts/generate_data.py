import os
import random
from datetime import datetime, timedelta, timezone

import psycopg2

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tsdb")
DB_USER = os.getenv("DB_USER", "tsadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tsadminpass")


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def seed_devices(conn, num_devices=50):
    locations = ["factory-1", "factory-2", "dc-1", "dc-2"]
    types = ["sensor", "gateway", "edge-node"]

    with conn.cursor() as cur:
        for i in range(1, num_devices + 1):
            cur.execute(
                """
                INSERT INTO devices (device_name, device_type, location)
                VALUES (%s, %s, %s)
                ON CONFLICT (device_id) DO NOTHING;
                """,
                (
                    f"device-{i:03d}",
                    random.choice(types),
                    random.choice(locations),
                ),
            )
    conn.commit()


def generate_metric_row(device_id, base_time, step_minutes, state):
    # Random walk around baseline
    state["cpu"] = max(0.0, min(100.0, state["cpu"] + random.uniform(-5, 5)))
    state["mem"] = max(64.0, state["mem"] + random.uniform(-50, 50))
    state["temp"] = max(10.0, state["temp"] + random.uniform(-1, 1))

    # Occasional errors
    if random.random() < 0.01:
        error_code = random.choice([1001, 2002, 5000])
        status = "DEGRADED"
    else:
        error_code = None
        status = "OK"

    return (
        base_time + timedelta(minutes=step_minutes),
        device_id,
        state["cpu"],
        state["mem"],
        state["temp"],
        error_code,
        status,
    )


def seed_metrics(conn, hours=24, devices=50, step_minutes=1):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours)

    # Simple state per device for more realistic trends
    device_state = {
        device_id: {"cpu": random.uniform(20, 60),
                    "mem": random.uniform(512, 4096),
                    "temp": random.uniform(20, 40)}
        for device_id in range(1, devices + 1)
    }

    total_rows = 0
    with conn.cursor() as cur:
        for device_id in range(1, devices + 1):
            t = start_time
            rows = []
            step = 0
            while t < now:
                row = generate_metric_row(device_id, start_time, step_minutes=step, state=device_state[device_id])
                rows.append(row)
                t += timedelta(minutes=step_minutes)
                step += step_minutes

                # Batch insert every 1000 rows for performance
                if len(rows) >= 1000:
                    cur.executemany(
                        """
                        INSERT INTO device_metrics (
                            time, device_id, cpu_usage, memory_usage, temperature, error_code, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                        """,
                        rows,
                    )
                    total_rows += len(rows)
                    rows = []

            if rows:
                cur.executemany(
                    """
                    INSERT INTO device_metrics (
                        time, device_id, cpu_usage, memory_usage, temperature, error_code, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    rows,
                )
                total_rows += len(rows)

    conn.commit()
    print(f"Inserted {total_rows} rows of metrics.")


if __name__ == "__main__":
    conn = get_conn()
    try:
        seed_devices(conn, num_devices=50)
        seed_metrics(conn, hours=72, devices=50, step_minutes=5)
    finally:
        conn.close()