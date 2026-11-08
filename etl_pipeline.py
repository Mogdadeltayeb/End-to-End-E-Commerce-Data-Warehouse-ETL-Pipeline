from datetime import datetime
import json
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

# Database connection details
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASS = "your_password"  # استبدل بكلمة المرور الخاصة بك
DB_PORT = "5432"
DB_NAME = "ecommerce_db"


def run_etl_pipeline():
  print("🚀 Starting ETL Pipeline Execution...\n")

  try:
    # 1. Connect to PostgreSQL
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
    )
    cursor = conn.cursor()
    print("✅ Connected to database successfully.")

    # ----------------------------------------------------
    # STEP A: Create Staging Tables
    # ----------------------------------------------------
    print(
        "\n⏳ Step 1: Creating Staging Tables (stg_*) in PostgreSQL..."
    )
    staging_sql = """
        DROP TABLE IF EXISTS stg_orders, stg_clickstream, stg_shipping_costs CASCADE;

        -- Staging Orders & Items Joined View/Table
        CREATE TABLE stg_orders AS
        SELECT 
            o.order_id,
            o.user_id,
            o.order_status,
            o.total_amount,
            o.shipping_fee,
            o.tax_amount,
            o.created_at AS order_date,
            p.payment_method,
            p.payment_status,
            s.carrier_name,
            s.shipping_status
        FROM orders o
        LEFT JOIN payments p ON o.order_id = p.order_id
        LEFT JOIN shipments s ON o.order_id = s.order_id;

        -- Staging Clickstream (JSON Source)
        CREATE TABLE stg_clickstream (
            event_id VARCHAR(50),
            user_id INT,
            session_id VARCHAR(50),
            action VARCHAR(50),
            product_id INT,
            device_type VARCHAR(50),
            browser VARCHAR(50),
            ip_address VARCHAR(50),
            timestamp TIMESTAMP
        );

        -- Staging Shipping Partners (CSV Source)
        CREATE TABLE stg_shipping_costs (
            carrier_name VARCHAR(100),
            service_zone VARCHAR(100),
            base_shipping_rate NUMERIC(10, 2),
            fuel_surcharge_pct NUMERIC(5, 3),
            target_sla_days INT,
            carrier_contact_email VARCHAR(100)
        );
        """
    cursor.execute(staging_sql)
    conn.commit()
    print("✅ Staging tables created successfully.")

    # ----------------------------------------------------
    # STEP B: Extract, Transform & Load JSON (Clickstream)
    # ----------------------------------------------------
    print(
        "\n⏳ Step 2: Processing & Loading 'clickstream_logs.json' to Staging..."
    )
    # Updated path to point inside 'External Data' folder
    with open(
        "External Data/clickstream_logs.json", "r", encoding="utf-8"
    ) as f:
      clickstream_data = json.load(f)

    clickstream_tuples = []
    for row in clickstream_data:
      clickstream_tuples.append((
          row["event_id"],
          row["user_id"],
          row["session_id"],
          row["action"],
          row["product_id"],
          row["device_type"],
          row["browser"],
          row["ip_address"],
          datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
      ))

    execute_batch(
        cursor,
        """
        INSERT INTO stg_clickstream (event_id, user_id, session_id, action, product_id, device_type, browser, ip_address, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """,
        clickstream_tuples,
    )
    conn.commit()
    print(
        f"✅ Loaded {len(clickstream_tuples)} records into 'stg_clickstream'."
    )

    # ----------------------------------------------------
    # STEP C: Extract, Transform & Load CSV (Shipping Partners)
    # ----------------------------------------------------
    print(
        "\n⏳ Step 3: Processing & Loading 'shipping_partners.csv' to"
        " Staging..."
    )
    # Updated path to point inside 'External Data' folder
    df_shipping = pd.read_csv("External Data/shipping_partners.csv")

    # Data Transformation: Clean column names and handle missing values if any
    df_shipping.fillna(0, inplace=True)

    shipping_tuples = [tuple(row) for row in df_shipping.to_numpy()]

    execute_batch(
        cursor,
        """
        INSERT INTO stg_shipping_costs (carrier_name, service_zone, base_shipping_rate, fuel_surcharge_pct, target_sla_days, carrier_contact_email)
        VALUES (%s, %s, %s, %s, %s, %s);
    """,
        shipping_tuples,
    )
    conn.commit()
    print(
        f"✅ Loaded {len(shipping_tuples)} records into 'stg_shipping_costs'."
    )

    print(
        "\n🎉 ETL Pipeline executed successfully! Staging layer is fully"
        " prepared."
    )

    cursor.close()
    conn.close()

  except Exception as error:
    print("❌ ETL Pipeline Error:", error)


if __name__ == "__main__":
  run_etl_pipeline()