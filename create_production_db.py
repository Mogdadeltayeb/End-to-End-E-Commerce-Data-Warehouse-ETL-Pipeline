import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection settings (before creating the target database)
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASS = "your_password"  # Replace with your PostgreSQL password
DB_PORT = "5432"
TARGET_DB_NAME = "ecommerce_db"

def create_database_and_tables():
    try:
        print("🔄 Connecting to PostgreSQL server...")
        # 1. Connect to PostgreSQL and create the database if it doesn't exist
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if the database already exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{TARGET_DB_NAME}';")
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME};")
            print(f"✅ Database '{TARGET_DB_NAME}' created successfully.")
        else:
            print(f"ℹ️ Database '{TARGET_DB_NAME}' already exists.")

        cursor.close()
        conn.close()

        print("🔄 Connecting to the target database to create tables...")
        # 2. Connect to the new database to create the tables
        target_conn = psycopg2.connect(
            host=DB_HOST,
            database=TARGET_DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        target_cursor = target_conn.cursor()

        # SQL script to create all 14 tables with relations
        tables_sql = """
        -- Enable UUID extension if needed
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- 1. Users table
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            email VARCHAR(150) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            phone VARCHAR(20),
            role VARCHAR(20) DEFAULT 'customer',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. Customer addresses table
        CREATE TABLE IF NOT EXISTS addresses (
            address_id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
            address_line1 VARCHAR(255) NOT NULL,
            address_line2 VARCHAR(255),
            city VARCHAR(100) NOT NULL,
            state VARCHAR(100),
            postal_code VARCHAR(20) NOT NULL,
            country VARCHAR(100) NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 3. Product categories table
        CREATE TABLE IF NOT EXISTS categories (
            category_id SERIAL PRIMARY KEY,
            parent_category_id INT REFERENCES categories(category_id) ON DELETE SET NULL,
            category_name VARCHAR(100) NOT NULL,
            slug VARCHAR(120) UNIQUE NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE
        );

        -- 4. Products table
        CREATE TABLE IF NOT EXISTS products (
            product_id SERIAL PRIMARY KEY,
            category_id INT REFERENCES categories(category_id) ON DELETE SET NULL,
            product_name VARCHAR(200) NOT NULL,
            slug VARCHAR(250) UNIQUE NOT NULL,
            description TEXT,
            base_price NUMERIC(12, 2) NOT NULL,
            cost_price NUMERIC(12, 2),
            sku VARCHAR(100) UNIQUE NOT NULL,
            is_featured BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 5. Inventory table
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id SERIAL PRIMARY KEY,
            product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
            warehouse_location VARCHAR(100) NOT NULL,
            stock_quantity INT NOT NULL DEFAULT 0,
            low_stock_threshold INT DEFAULT 5,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 6. Shopping carts table
        CREATE TABLE IF NOT EXISTS carts (
            cart_id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 7. Cart items table
        CREATE TABLE IF NOT EXISTS cart_items (
            cart_item_id SERIAL PRIMARY KEY,
            cart_id INT REFERENCES carts(cart_id) ON DELETE CASCADE,
            product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
            quantity INT NOT NULL CHECK (quantity > 0),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 8. Coupons table
        CREATE TABLE IF NOT EXISTS coupons (
            coupon_id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            discount_type VARCHAR(20) CHECK (discount_type IN ('percentage', 'fixed')),
            discount_value NUMERIC(10, 2) NOT NULL,
            min_spend NUMERIC(10, 2) DEFAULT 0.00,
            usage_limit INT,
            used_count INT DEFAULT 0,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );

        -- 9. Orders table
        CREATE TABLE IF NOT EXISTS orders (
            order_id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
            shipping_address_id INT REFERENCES addresses(address_id) ON DELETE SET NULL,
            coupon_id INT REFERENCES coupons(coupon_id) ON DELETE SET NULL,
            order_status VARCHAR(30) DEFAULT 'Pending',
            total_amount NUMERIC(12, 2) NOT NULL,
            shipping_fee NUMERIC(10, 2) DEFAULT 0.00,
            tax_amount NUMERIC(10, 2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 10. Order items table
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id SERIAL PRIMARY KEY,
            order_id INT REFERENCES orders(order_id) ON DELETE CASCADE,
            product_id INT REFERENCES products(product_id) ON DELETE SET NULL,
            quantity INT NOT NULL,
            unit_price_at_purchase NUMERIC(12, 2) NOT NULL,
            total_item_price NUMERIC(12, 2) NOT NULL
        );

        -- 11. Payments table
        CREATE TABLE IF NOT EXISTS payments (
            payment_id SERIAL PRIMARY KEY,
            order_id INT REFERENCES orders(order_id) ON DELETE CASCADE,
            payment_method VARCHAR(50) NOT NULL,
            payment_status VARCHAR(30) DEFAULT 'Pending',
            transaction_reference VARCHAR(255),
            amount_paid NUMERIC(12, 2) NOT NULL,
            paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 12. Shipments table
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id SERIAL PRIMARY KEY,
            order_id INT REFERENCES orders(order_id) ON DELETE CASCADE,
            carrier_name VARCHAR(100) NOT NULL,
            tracking_number VARCHAR(150),
            shipping_status VARCHAR(30) DEFAULT 'Processing',
            estimated_delivery_date DATE,
            shipped_at TIMESTAMP,
            delivered_at TIMESTAMP
        );

        -- 13. Product reviews table
        CREATE TABLE IF NOT EXISTS product_reviews (
            review_id SERIAL PRIMARY KEY,
            product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
            user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
            rating INT CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 14. Wishlists table
        CREATE TABLE IF NOT EXISTS wishlists (
            wishlist_id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
            product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id)
        );
        """

        print("🔄 Executing SQL script to create tables and relations...")
        target_cursor.execute(tables_sql)
        target_conn.commit()
        print("✅ All e-commerce tables and relations have been created successfully!")

        target_cursor.close()
        target_conn.close()

    except Exception as error:
        print("❌ An error occurred while executing the script:", error)

if __name__ == "__main__":
    create_database_and_tables()