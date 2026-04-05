import psycopg2
from generate_data import get_conn
from datetime import datetime


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def query_top_hottest_devices(cur):
    print_header("Top 5 Hottest Devices (Last 24 Hours)")
    cur.execute("""
        SELECT
            d.device_name,
            d.location,
            ROUND(MAX(dm.temperature)::numeric, 2) AS max_temp
        FROM device_metrics dm
        JOIN devices d ON dm.device_id = d.device_id
        WHERE dm.time >= NOW() - INTERVAL '24 hours'
        GROUP BY d.device_name, d.location
        ORDER BY max_temp DESC
        LIMIT 5;
    """)
    rows = cur.fetchall()
    print(f"{'Device':<15} {'Location':<15} {'Max Temp (°C)'}")
    print("-" * 45)
    for row in rows:
        print(f"{row[0]:<15} {row[1]:<15} {row[2]}")


def query_error_rate(cur):
    print_header("Top 10 Devices by Error Rate (Last 24 Hours)")
    cur.execute("""
        SELECT
            d.device_name,
            COUNT(*) FILTER (WHERE dm.error_code IS NOT NULL AND dm.error_code != 0) AS errors,
            COUNT(*) AS total,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE dm.error_code IS NOT NULL AND dm.error_code != 0)
                / NULLIF(COUNT(*), 0), 2
            ) AS error_rate_pct
        FROM device_metrics dm
        JOIN devices d ON dm.device_id = d.device_id
        WHERE dm.time >= NOW() - INTERVAL '24 hours'
        GROUP BY d.device_name
        ORDER BY error_rate_pct DESC NULLS LAST
        LIMIT 10;
    """)
    rows = cur.fetchall()
    print(f"{'Device':<15} {'Errors':<10} {'Total':<10} {'Error Rate %'}")
    print("-" * 50)
    for row in rows:
        print(f"{row[0]:<15} {row[1]:<10} {row[2]:<10} {row[3]}")


def query_hourly_aggregates(cur):
    print_header("Hourly CPU Stats via Continuous Aggregate (Last 3 Hours)")
    cur.execute("""
        SELECT
            bucket,
            d.device_name,
            ROUND(avg_cpu_usage::numeric, 2) AS avg_cpu,
            ROUND(max_cpu_usage::numeric, 2) AS max_cpu,
            error_count
        FROM device_metrics_hourly h
        JOIN devices d ON h.device_id = d.device_id
        WHERE bucket >= NOW() - INTERVAL '3 hours'
          AND d.device_name IN ('device-001', 'device-002', 'device-003')
        ORDER BY bucket DESC, d.device_name;
    """)
    rows = cur.fetchall()
    print(f"{'Bucket':<25} {'Device':<15} {'Avg CPU':<12} {'Max CPU':<12} {'Errors'}")
    print("-" * 70)
    for row in rows:
        print(f"{str(row[0]):<25} {row[1]:<15} {row[2]:<12} {row[3]:<12} {row[4]}")


def query_device_summary(cur):
    print_header("Fleet Summary (Last 24 Hours)")
    cur.execute("""
        SELECT
            COUNT(DISTINCT d.device_id) AS total_devices,
            COUNT(*) AS total_readings,
            ROUND(AVG(dm.cpu_usage)::numeric, 2) AS avg_cpu,
            ROUND(AVG(dm.temperature)::numeric, 2) AS avg_temp,
            SUM(CASE WHEN dm.error_code IS NOT NULL AND dm.error_code != 0 THEN 1 ELSE 0 END) AS total_errors
        FROM device_metrics dm
        JOIN devices d ON dm.device_id = d.device_id
        WHERE dm.time >= NOW() - INTERVAL '24 hours';
    """)
    row = cur.fetchone()
    print(f"  Total Devices    : {row[0]}")
    print(f"  Total Readings   : {row[1]}")
    print(f"  Avg CPU Usage    : {row[2]}%")
    print(f"  Avg Temperature  : {row[3]}°C")
    print(f"  Total Errors     : {row[4]}")


if __name__ == "__main__":
    print(f"\n IoT Timeseries Analytics Report")
    print(f" Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            query_device_summary(cur)
            query_top_hottest_devices(cur)
            query_error_rate(cur)
            query_hourly_aggregates(cur)
        print("\n" + "=" * 60)
        print("  Analytics complete.")
        print("=" * 60 + "\n")
    finally:
        conn.close()