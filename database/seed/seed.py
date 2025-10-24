import os
import json
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash


load_dotenv()

MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST'),
    'user': os.environ.get('MYSQL_USER'),
    'password': os.environ.get('MYSQL_PASSWORD'),
    'database': os.environ.get('MYSQL_DB'),
    'port': os.environ.get('MYSQL_PORT')
}


def execute_sql_script(cursor, sql_script):
    commands = sql_script.split(';')
    for command in commands:
        stripped_command = command.strip()
        if stripped_command:
            try:
                cursor.execute(stripped_command)
            except mysql.connector.Error as err:
                print(f"Error executing command: {stripped_command}\n{err}")
                raise


def seed_database():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    instance_dir = os.path.join(project_root, 'database')
    schema_file = os.path.join(instance_dir, 'seed', 'schema.sql')
    data_file = os.path.join(instance_dir, 'seed', 'data.json')

    if not os.path.exists(schema_file):
        print(f"Error: Schema file not found at {schema_file}")
        return

    if not os.path.exists(data_file):
        print(f"Error: Data file not found at {data_file}")
        return

    connection = None
    try:
        connection = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            port=MYSQL_CONFIG['port']
        )
        cursor = connection.cursor()
        db_name = MYSQL_CONFIG['database']

        print(f"Dropping database '{db_name}' if exists...")
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")

        print(f"Creating database '{db_name}'...")
        cursor.execute(f"CREATE DATABASE {db_name}")
        cursor.execute(f"USE {db_name}")
        print(f"Database '{db_name}' selected.")

        print("\nMembaca dan menjalankan skema SQL...")
        with open(schema_file, 'r') as f:
            sql_script = f.read()
        execute_sql_script(cursor, sql_script)
        print("Skema tabel berhasil dibuat.")

        print("\nMembaca data JSON...")
        with open(data_file, 'r') as f:
            data = json.load(f)
        print("Data JSON berhasil dibaca.")

        print("\nMemasukkan data awal...")

        # Content
        if 'content' in data:
            content_data = [(item['key'], item['value']) for item in data['content']]
            cursor.executemany(
                "INSERT INTO content (`key`, `value`) VALUES (%s, %s)",
                content_data
            )
            connection.commit()
            print(f"- Data 'content' ({len(content_data)} baris) berhasil dimasukkan.")

        # Users
        if 'users' in data:
            users_to_add = [
                (
                    user['username'], user['email'], generate_password_hash(user['password']),
                    user.get('phone'), user.get('address_line_1'), user.get('address_line_2'),
                    user.get('city'), user.get('province'), user.get('postal_code'),
                    user.get('is_admin', 0)
                )
                for user in data['users']
            ]

            reg_count = data.get('regular_users_count', 0)
            reg_pass = data.get('regular_user_password', 'password123')
            hashed_reg_pass = generate_password_hash(reg_pass)

            for i in range(1, reg_count + 1):
                users_to_add.append(
                    (f'user{i}', f'user{i}@example.com', hashed_reg_pass,
                     None, None, None, None, None, None, 0)
                )

            cursor.executemany(
                """
                INSERT INTO users (
                    username, email, password, phone, address_line_1, address_line_2,
                    city, province, postal_code, is_admin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                users_to_add
            )
            connection.commit()
            print(f"- Data 'users' ({len(users_to_add)} baris) berhasil dimasukkan.")

        # Categories
        if 'categories' in data:
            category_data = [(item['name'],) for item in data['categories']]
            cursor.executemany(
                "INSERT INTO categories (name) VALUES (%s)",
                category_data
            )
            connection.commit()
            print(f"- Data 'categories' ({len(category_data)} baris) berhasil dimasukkan.")

        # Products
        if 'products' in data:
            products_to_insert = [
                (
                    p['name'], p['price'], p.get('discount_price'), p['description'],
                    p['category_id'], p.get('colors'), p.get('popularity', 0),
                    p['image_url'], json.dumps(p.get('additional_image_urls', [])),
                    p['stock'], p['has_variants'], p.get('weight_grams', 0), p.get('sku')
                )
                for p in data['products']
            ]
            cursor.executemany(
                """
                INSERT INTO products (
                    name, price, discount_price, description, category_id, colors,
                    popularity, image_url, additional_image_urls, stock,
                    has_variants, weight_grams, sku
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                products_to_insert
            )
            connection.commit()
            print(f"- Data 'products' ({len(products_to_insert)} baris) berhasil dimasukkan.")

        # Variants
        if 'variants' in data:
            variants_to_insert = [
                (v['product_id'], v['size'], v['stock'],
                 v.get('weight_grams', 0), v.get('sku'))
                for v in data['variants']
            ]
            cursor.executemany(
                """
                INSERT INTO product_variants (product_id, size, stock, weight_grams, sku)
                VALUES (%s, %s, %s, %s, %s)
                """,
                variants_to_insert
            )
            connection.commit()
            print(f"- Data 'product_variants' ({len(variants_to_insert)} baris) berhasil dimasukkan.")

            variant_product_ids = {v[0] for v in variants_to_insert}
            for pid in variant_product_ids:
                cursor.execute(
                    """
                    UPDATE products
                    SET stock = (
                        SELECT SUM(stock)
                        FROM product_variants
                        WHERE product_id = %s
                    )
                    WHERE id = %s AND has_variants = 1
                    """,
                    (pid, pid)
                )
            connection.commit()
            print(f"- Stok total produk bervarian ({len(variant_product_ids)} produk) diperbarui.")

        # Orders
        if 'orders' in data:
            order_data = [
                (
                    o['id'], o['user_id'], o['order_date'], o['subtotal'],
                    o.get('discount_amount', 0), o.get('shipping_cost', 0),
                    o['total_amount'], o.get('voucher_code'), o['status'],
                    o.get('payment_method'), o.get('payment_transaction_id'),
                    o.get('shipping_name'), o.get('shipping_phone'),
                    o.get('shipping_address_line_1'), o.get('shipping_address_line_2'),
                    o.get('shipping_city'), o.get('shipping_province'),
                    o.get('shipping_postal_code'), o.get('tracking_number')
                )
                for o in data['orders']
            ]
            cursor.executemany(
                """
                INSERT INTO orders (
                    id, user_id, order_date, subtotal, discount_amount,
                    shipping_cost, total_amount, voucher_code, status,
                    payment_method, payment_transaction_id, shipping_name,
                    shipping_phone, shipping_address_line_1, shipping_address_line_2,
                    shipping_city, shipping_province, shipping_postal_code, tracking_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                order_data
            )
            connection.commit()
            print(f"- Data 'orders' ({len(order_data)} baris) berhasil dimasukkan.")

        # Order Items
        if 'order_items' in data:
            order_item_data = [
                (
                    oi['id'], oi['order_id'], oi['product_id'], oi.get('variant_id'),
                    oi['quantity'], oi['price'], oi.get('size_at_order')
                )
                for oi in data['order_items']
            ]
            cursor.executemany(
                """
                INSERT INTO order_items (
                    id, order_id, product_id, variant_id, quantity, price, size_at_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                order_item_data
            )
            connection.commit()
            print(f"- Data 'order_items' ({len(order_item_data)} baris) berhasil dimasukkan.")

        # Reviews
        if 'reviews' in data:
            review_data = [
                (
                    r['product_id'], r['user_id'], r['rating'],
                    r['comment'], r.get('created_at')
                )
                for r in data['reviews']
            ]
            cursor.executemany(
                """
                INSERT INTO reviews (product_id, user_id, rating, comment, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                review_data
            )
            connection.commit()
            print(f"- Data 'reviews' ({len(review_data)} baris) berhasil dimasukkan.")

        # Vouchers
        if 'vouchers' in data:
            voucher_data = [
                (
                    v['code'], v['type'], v['value'], v.get('max_uses'),
                    v.get('use_count', 0), v.get('start_date'), v.get('end_date'),
                    v.get('min_purchase_amount', 0), v.get('is_active', 1)
                )
                for v in data['vouchers']
            ]
            cursor.executemany(
                """
                INSERT INTO vouchers (
                    code, type, value, max_uses, use_count,
                    start_date, end_date, min_purchase_amount, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                voucher_data
            )
            connection.commit()
            print(f"- Data 'vouchers' ({len(voucher_data)} baris) berhasil dimasukkan.")

        print("\nSetup database dan seeding selesai.")

    except mysql.connector.Error as err:
        print(f"Terjadi kesalahan MySQL: {err}")
    except FileNotFoundError as e:
        print(f"File tidak ditemukan: {e}")
    except json.JSONDecodeError as e:
        print(f"Error saat membaca file JSON: {e}")
    except Exception as e:
        print(f"Terjadi kesalahan tak terduga: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("Koneksi database ditutup.")


if __name__ == '__main__':
    seed_database()