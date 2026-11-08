import psycopg2

# Database connection details
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASS = "your_password"  # استبدل بكلمة المرور الخاصة بك
DB_PORT = "5432"
DB_NAME = "ecommerce_db"


def build_star_schema():
  print("🚀 Starting Data Warehouse (Star Schema) Build Process...\n")

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

    # Drop existing tables
    print("⏳ Dropping existing DWH tables if any...")
    cursor.execute("""
        DROP TABLE IF EXISTS fact_sales, dim_customers, dim_products, dim_date, dim_shipping CASCADE;
    """)
    conn.commit()

    # 1. dim_date
    print("⏳ Building dim_date...")
    cursor.execute("""
        CREATE TABLE dim_date AS
        SELECT DISTINCT
            CAST(TO_CHAR(created_at, 'YYYYMMDD') AS INT) AS date_id,
            CAST(created_at AS DATE) AS full_date,
            EXTRACT(YEAR FROM created_at) AS year,
            EXTRACT(QUARTER FROM created_at) AS quarter,
            EXTRACT(MONTH FROM created_at) AS month,
            TO_CHAR(created_at, 'Month') AS month_name,
            EXTRACT(WEEK FROM created_at) AS week_of_year,
            EXTRACT(DOW FROM created_at) AS day_of_week,
            TO_CHAR(created_at, 'Day') AS day_name
        FROM orders;

        ALTER TABLE dim_date ADD PRIMARY KEY (date_id);
    """)
    conn.commit()

    # 2. dim_customers
    print("⏳ Building dim_customers...")
    cursor.execute("""
        CREATE TABLE dim_customers AS
        SELECT 
            u.user_id AS customer_id,
            u.first_name,
            u.last_name,
            u.email,
            u.phone,
            a.city,
            a.state,
            a.country,
            u.created_at AS registration_date
        FROM users u
        LEFT JOIN addresses a ON u.user_id = a.user_id AND a.is_default = TRUE;

        ALTER TABLE dim_customers ADD PRIMARY KEY (customer_id);
    """)
    conn.commit()

    # 3. dim_products
    print("⏳ Building dim_products...")
    cursor.execute("""
        CREATE TABLE dim_products AS
        SELECT 
            p.product_id,
            p.product_name,
            p.sku,
            c.category_name,
            p.base_price,
            p.cost_price,
            p.is_active
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.category_id;

        ALTER TABLE dim_products ADD PRIMARY KEY (product_id);
    """)
    conn.commit()

    # 4. dim_shipping
    print("⏳ Building dim_shipping...")
    cursor.execute("""
        CREATE TABLE dim_shipping AS
        SELECT 
            ROW_NUMBER() OVER() AS shipping_dim_id,
            carrier_name,
            service_zone,
            base_shipping_rate,
            target_sla_days
        FROM stg_shipping_costs;

        ALTER TABLE dim_shipping ADD PRIMARY KEY (shipping_dim_id);
    """)
    conn.commit()

    # 5. fact_sales
    print("⏳ Building fact_sales and populating core metrics...")
    cursor.execute("""
        CREATE TABLE fact_sales (
            sale_id SERIAL PRIMARY KEY,
            order_id INT,
            customer_id INT REFERENCES dim_customers(customer_id),
            product_id INT REFERENCES dim_products(product_id),
            date_id INT REFERENCES dim_date(date_id),
            quantity INT,
            unit_price NUMERIC(12, 2),
            total_item_price NUMERIC(12, 2),
            shipping_fee NUMERIC(10, 2),
            tax_amount NUMERIC(10, 2),
            profit_margin NUMERIC(12, 2)
        );

        INSERT INTO fact_sales (
            order_id, customer_id, product_id, date_id, 
            quantity, unit_price, total_item_price, 
            shipping_fee, tax_amount, profit_margin
        )
        SELECT 
            o.order_id,
            o.user_id,
            oi.product_id,
            CAST(TO_CHAR(o.created_at, 'YYYYMMDD') AS INT),
            oi.quantity,
            oi.unit_price_at_purchase,
            oi.total_item_price,
            o.shipping_fee,
            o.tax_amount,
            ROUND((oi.total_item_price - (COALESCE(p.cost_price, oi.unit_price_at_purchase * 0.6) * oi.quantity)), 2) AS profit_margin
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.product_id;
    """)
    conn.commit()

    print(
        "✅ Data Warehouse (Star Schema) tables created and populated"
        " successfully!"
    )

    cursor.close()
    conn.close()

  except Exception as error:
    print("❌ DWH Build Error:", error)


if __name__ == "__main__":
  build_star_schema()