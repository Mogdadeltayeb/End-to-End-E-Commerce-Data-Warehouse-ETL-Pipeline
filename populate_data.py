import random
import string
from datetime import datetime, timedelta
from faker import Faker
import psycopg2
from psycopg2.extras import execute_batch

# Database connection details
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASS = "your_password"  # استبدل بكلمة المرور الخاصة بك
DB_PORT = "5432"
DB_NAME = "ecommerce_db"

fake = Faker()

# Helper functions for random strings & digits
val_chars = string.ascii_uppercase + string.digits

def get_random_string(length=8):
    return ''.join(random.choices(val_chars, k=length))

def get_random_digits(length=10):
    return ''.join(random.choices(string.digits, k=length))

def populate_ecommerce_database():
    try:
        print("🔄 Connecting to 'ecommerce_db'...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        cursor = conn.cursor()
        print("✅ Connected successfully.")

        # 🧹 Truncate existing tables to avoid duplicate key conflicts if re-run
        print("🧹 Clearing existing data to prevent conflicts...")
        cursor.execute("""
            TRUNCATE TABLE 
                order_items, payments, shipments, product_reviews, 
                wishlists, cart_items, carts, inventory, orders, 
                coupons, addresses, products, categories, users 
            CASCADE;
        """)
        conn.commit()

        # ----------------------------------------------------
        # 1. Categories (20 categories & subcategories)
        # ----------------------------------------------------
        print("⏳ Inserting Categories...")
        parent_categories = ["Electronics", "Clothing", "Home & Kitchen", "Books", "Sports & Outdoors"]
        category_ids = []

        for parent in parent_categories:
            cursor.execute(
                "INSERT INTO categories (category_name, slug, description) VALUES (%s, %s, %s) RETURNING category_id;",
                (parent, parent.lower().replace(" ", "-"), fake.text(max_nb_chars=100))
            )
            p_id = cursor.fetchone()[0]
            category_ids.append(p_id)

            # Insert subcategories
            for i in range(3):
                sub_name = f"{parent} Sub {i+1}"
                cursor.execute(
                    "INSERT INTO categories (parent_category_id, category_name, slug, description) VALUES (%s, %s, %s, %s) RETURNING category_id;",
                    (p_id, sub_name, f"{sub_name.lower().replace(' ', '-')}-{random.randint(1000, 9999)}", fake.text(max_nb_chars=100))
                )
                category_ids.append(cursor.fetchone()[0])
        
        conn.commit()

        # ----------------------------------------------------
        # 2. Products & Inventory (500 Products)
        # ----------------------------------------------------
        print("⏳ Inserting 500 Products & Inventory...")
        product_ids = []

        for i in range(1, 501):
            p_name = f"{fake.company()} {fake.word().capitalize()}"
            base_price = round(random.uniform(10.0, 1500.0), 2)
            cost_price = round(base_price * random.uniform(0.5, 0.8), 2)
            sku = f"SKU-{get_random_string(8)}"

            cursor.execute("""
                INSERT INTO products (category_id, product_name, slug, description, base_price, cost_price, sku)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING product_id;
            """, (
                random.choice(category_ids),
                p_name,
                f"prod-{i}-{get_random_string(4).lower()}",
                fake.paragraph(nb_sentences=2),
                base_price,
                cost_price,
                sku
            ))
            prod_id = cursor.fetchone()[0]
            product_ids.append((prod_id, base_price))

            # Inventory
            cursor.execute("""
                INSERT INTO inventory (product_id, warehouse_location, stock_quantity)
                VALUES (%s, %s, %s);
            """, (
                prod_id,
                f"Warehouse-{random.choice(['A', 'B', 'C'])}",
                random.randint(10, 500)
            ))

        conn.commit()

        # ----------------------------------------------------
        # 3. Users & Addresses (2,000 Users)
        # ----------------------------------------------------
        print("⏳ Inserting 2,000 Users & Addresses...")
        user_data = []

        for _ in range(2000):
            email = f"{get_random_string(6).lower()}_{fake.unique.email()}"
            pass_hash = "hashed_secret_password"
            fname = fake.first_name()
            lname = fake.last_name()
            phone = fake.phone_number()[:20]
            user_data.append((email, pass_hash, fname, lname, phone))

        execute_batch(cursor, """
            INSERT INTO users (email, password_hash, first_name, last_name, phone)
            VALUES (%s, %s, %s, %s, %s);
        """, user_data)
        conn.commit()

        # Fetch inserted user_ids
        cursor.execute("SELECT user_id FROM users;")
        user_ids = [r[0] for r in cursor.fetchall()]

        # Insert Addresses for users
        address_data = []
        for u_id in user_ids:
            address_data.append((
                u_id,
                fake.street_address(),
                fake.city(),
                fake.state(),
                fake.zipcode()[:20],
                fake.country(),
                True
            ))

        execute_batch(cursor, """
            INSERT INTO addresses (user_id, address_line1, city, state, postal_code, country, is_default)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, address_data)
        conn.commit()

        # Fetch address_ids mapped to users
        cursor.execute("SELECT address_id, user_id FROM addresses;")
        user_address_map = {row[1]: row[0] for row in cursor.fetchall()}

        # ----------------------------------------------------
        # 4. Coupons (20 Coupons)
        # ----------------------------------------------------
        print("⏳ Inserting Coupons...")
        coupon_ids = []
        for i in range(20):
            code = f"DISC{get_random_string(5)}"
            cursor.execute("""
                INSERT INTO coupons (code, discount_type, discount_value, min_spend, expires_at)
                VALUES (%s, %s, %s, %s, %s) RETURNING coupon_id;
            """, (
                code,
                random.choice(['percentage', 'fixed']),
                random.choice([10, 15, 20, 25, 50]),
                50.00,
                datetime.now() + timedelta(days=180)
            ))
            coupon_ids.append(cursor.fetchone()[0])
        
        conn.commit()

        # ----------------------------------------------------
        # 5. Orders & Order Items & Payments & Shipments (10,000 Orders)
        # ----------------------------------------------------
        print("⏳ Inserting 10,000 Orders with Items, Payments & Shipments...")
        
        statuses = ['Completed', 'Completed', 'Completed', 'Shipped', 'Pending', 'Cancelled']
        pay_methods = ['Credit Card', 'PayPal', 'Apple Pay', 'Cash on Delivery']
        carriers = ['FedEx', 'DHL', 'Aramex', 'UPS']

        for i in range(1, 10001):
            u_id = random.choice(user_ids)
            addr_id = user_address_map.get(u_id)
            status = random.choice(statuses)
            coupon_id = random.choice(coupon_ids) if random.random() < 0.2 else None
            order_date = fake.date_time_between(start_date='-2y', end_date='now')

            # Generate items for this order
            num_items = random.randint(1, 4)
            chosen_prods = random.sample(product_ids, num_items)

            subtotal = 0.0
            items_to_insert = []

            for p_id, price in chosen_prods:
                qty = random.randint(1, 3)
                total_item_price = round(price * qty, 2)
                subtotal += total_item_price
                items_to_insert.append((p_id, qty, price, total_item_price))

            shipping_fee = 15.00
            tax_amount = round(subtotal * 0.05, 2)
            total_amount = round(subtotal + shipping_fee + tax_amount, 2)

            # Insert Order
            cursor.execute("""
                INSERT INTO orders (user_id, shipping_address_id, coupon_id, order_status, total_amount, shipping_fee, tax_amount, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING order_id;
            """, (u_id, addr_id, coupon_id, status, total_amount, shipping_fee, tax_amount, order_date, order_date))
            order_id = cursor.fetchone()[0]

            # Insert Order Items
            for item in items_to_insert:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price_at_purchase, total_item_price)
                    VALUES (%s, %s, %s, %s, %s);
                """, (order_id, item[0], item[1], item[2], item[3]))

            # Insert Payment
            pay_status = 'Completed' if status in ['Completed', 'Shipped'] else status
            cursor.execute("""
                INSERT INTO payments (order_id, payment_method, payment_status, transaction_reference, amount_paid, paid_at)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (order_id, random.choice(pay_methods), pay_status, f"TXN-{get_random_string(12)}", total_amount, order_date))

            # Insert Shipment
            if status in ['Completed', 'Shipped']:
                cursor.execute("""
                    INSERT INTO shipments (order_id, carrier_name, tracking_number, shipping_status, shipped_at)
                    VALUES (%s, %s, %s, %s, %s);
                """, (order_id, random.choice(carriers), f"TRK{get_random_digits(10)}", 'Delivered' if status == 'Completed' else 'In Transit', order_date + timedelta(hours=random.randint(12, 48))))

            # Commit batch every 1000 orders
            if i % 1000 == 0:
                conn.commit()
                print(f"   --> {i} Orders inserted...")

        conn.commit()

        # ----------------------------------------------------
        # 6. Reviews & Wishlists
        # ----------------------------------------------------
        print("⏳ Inserting Product Reviews & Wishlists...")
        review_data = []
        wishlist_data = []

        for _ in range(3000):
            review_data.append((
                random.choice([p[0] for p in product_ids]),
                random.choice(user_ids),
                random.randint(1, 5),
                fake.sentence()
            ))

        execute_batch(cursor, """
            INSERT INTO product_reviews (product_id, user_id, rating, comment)
            VALUES (%s, %s, %s, %s);
        """, review_data)

        for _ in range(2000):
            wishlist_data.append((
                random.choice(user_ids),
                random.choice([p[0] for p in product_ids])
            ))

        execute_batch(cursor, """
            INSERT INTO wishlists (user_id, product_id)
            VALUES (%s, %s) ON CONFLICT (user_id, product_id) DO NOTHING;
        """, wishlist_data)

        conn.commit()
        print("🎉 All tables successfully populated with thousands of records! Database is ready for ETL!")

        cursor.close()
        conn.close()

    except Exception as error:
        print("❌ Error populating database:", error)

if __name__ == "__main__":
    populate_ecommerce_database()