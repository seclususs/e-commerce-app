import sqlite3
import os
import json
from werkzeug.security import generate_password_hash

def seed_database():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    instance_dir = os.path.join(project_root, 'database')
    db_file = os.path.join(instance_dir, 'database.db')
    schema_file = os.path.join(instance_dir, 'seed', 'schema.sql')
    data_file = os.path.join(instance_dir, 'seed', 'data.json')

    if not os.path.exists(schema_file):
        print(f"Error: Schema file not found at {schema_file}")
        return
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at {data_file}")
        return

    os.makedirs(instance_dir, exist_ok=True)

    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"File database lama '{db_file}' berhasil dihapus.")

    connection = sqlite3.connect(db_file)
    print(f"Database '{db_file}' berhasil dibuat.")

    try:
        with connection:
            cursor = connection.cursor()

            print("\nMembaca dan menjalankan skema SQL...")
            with open(schema_file, 'r') as f:
                sql_script = f.read()
            cursor.executescript(sql_script)
            print("Skema tabel berhasil dibuat.")

            print("\nMembaca data JSON...")
            with open(data_file, 'r') as f:
                data = json.load(f)
            print("Data JSON berhasil dibaca.")

            print("\nMemasukkan data awal...")

            if 'content' in data:
                cursor.executemany("INSERT INTO content (key, value) VALUES (:key, :value)", data['content'])
                print(f"- Data 'content' ({len(data['content'])} baris) berhasil dimasukkan.")

            if 'users' in data:
                users_to_add = []
                for user in data['users']:
                    users_to_add.append((
                        user['username'], user['email'], generate_password_hash(user['password']),
                        user.get('phone'), user.get('address_line_1'), user.get('address_line_2'),
                        user.get('city'), user.get('province'), user.get('postal_code'),
                        user.get('is_admin', 0)
                    ))

                reg_count = data.get('regular_users_count', 0)
                reg_pass = data.get('regular_user_password', 'password123')
                hashed_reg_pass = generate_password_hash(reg_pass)
                for i in range(1, reg_count + 1):
                     users_to_add.append(
                        (f'user{i}', f'user{i}@example.com', hashed_reg_pass, None, None, None, None, None, None, 0)
                    )

                cursor.executemany("""
                    INSERT INTO users (username, email, password, phone, address_line_1, address_line_2, city, province, postal_code, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, users_to_add)
                print(f"- Data 'users' ({len(users_to_add)} baris) berhasil dimasukkan.")

            if 'categories' in data:
                cursor.executemany("INSERT INTO categories (name) VALUES (:name)", data['categories'])
                print(f"- Data 'categories' ({len(data['categories'])} baris) berhasil dimasukkan.")

            if 'products' in data:
                 products_to_insert = []
                 for p in data['products']:
                     products_to_insert.append((
                        p['name'], p['price'], p.get('discount_price'), p['description'],
                        p['category_id'], p.get('colors'), p.get('popularity', 0),
                        p['image_url'], json.dumps(p.get('additional_image_urls', [])),
                        p['stock'], p['has_variants'], p.get('weight_grams', 0), p.get('sku')
                     ))
                 cursor.executemany("""
                    INSERT INTO products (name, price, discount_price, description, category_id, colors, popularity, image_url, additional_image_urls, stock, has_variants, weight_grams, sku)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                 """, products_to_insert)
                 print(f"- Data 'products' ({len(products_to_insert)} baris) berhasil dimasukkan.")

            if 'variants' in data:
                cursor.executemany("""
                    INSERT INTO product_variants (product_id, size, stock, weight_grams, sku)
                    VALUES (:product_id, :size, :stock, :weight_grams, :sku)
                """, data['variants'])
                print(f"- Data 'product_variants' ({len(data['variants'])} baris) berhasil dimasukkan.")

                variant_product_ids = {v['product_id'] for v in data['variants']}
                for pid in variant_product_ids:
                    cursor.execute("""
                        UPDATE products SET stock = (SELECT SUM(stock) FROM product_variants WHERE product_id = ?)
                        WHERE id = ? AND has_variants = 1
                    """, (pid, pid))
                print(f"- Stok total untuk produk bervarian ({len(variant_product_ids)} produk) berhasil diperbarui.")

            if 'orders' in data:
                 cursor.executemany("""
                    INSERT INTO orders (id, user_id, order_date, subtotal, discount_amount, shipping_cost, total_amount, voucher_code, status, payment_method, payment_transaction_id, shipping_name, shipping_phone, shipping_address_line_1, shipping_address_line_2, shipping_city, shipping_province, shipping_postal_code, tracking_number)
                    VALUES (:id, :user_id, :order_date, :subtotal, :discount_amount, :shipping_cost, :total_amount, :voucher_code, :status, :payment_method, :payment_transaction_id, :shipping_name, :shipping_phone, :shipping_address_line_1, :shipping_address_line_2, :shipping_city, :shipping_province, :shipping_postal_code, :tracking_number)
                 """, data['orders'])
                 print(f"- Data 'orders' ({len(data['orders'])} baris) berhasil dimasukkan.")

            if 'order_items' in data:
                cursor.executemany("""
                    INSERT INTO order_items (id, order_id, product_id, variant_id, quantity, price, size_at_order)
                    VALUES (:id, :order_id, :product_id, :variant_id, :quantity, :price, :size_at_order)
                """, data['order_items'])
                print(f"- Data 'order_items' ({len(data['order_items'])} baris) berhasil dimasukkan.")

            if 'reviews' in data:
                cursor.executemany("""
                    INSERT INTO reviews (product_id, user_id, rating, comment, created_at)
                    VALUES (:product_id, :user_id, :rating, :comment, :created_at)
                """, data['reviews'])
                print(f"- Data 'reviews' ({len(data['reviews'])} baris) berhasil dimasukkan.")

            if 'vouchers' in data:
                cursor.executemany("""
                    INSERT INTO vouchers (code, type, value, max_uses, use_count, start_date, end_date, min_purchase_amount, is_active)
                    VALUES (:code, :type, :value, :max_uses, :use_count, :start_date, :end_date, :min_purchase_amount, :is_active)
                """, data['vouchers'])
                print(f"- Data 'vouchers' ({len(data['vouchers'])} baris) berhasil dimasukkan.")

            print("\nSetup database dan seeding selesai.")

    except sqlite3.Error as e:
        print(f"Terjadi kesalahan SQLite: {e}")
    except FileNotFoundError as e:
        print(f"File tidak ditemukan: {e}")
    except json.JSONDecodeError as e:
        print(f"Error saat membaca file JSON: {e}")
    except Exception as e:
        print(f"Terjadi kesalahan tak terduga: {e}")
    finally:
        if connection:
            connection.close()
            print("Koneksi database ditutup.")

if __name__ == '__main__':
    seed_database()