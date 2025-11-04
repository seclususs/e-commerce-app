import json
import os
import sys
from datetime import datetime

import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST"),
    "user": os.environ.get("MYSQL_USER"),
    "password": os.environ.get("MYSQL_PASSWORD"),
    "database": os.environ.get("MYSQL_DB"),
    "port": os.environ.get("MYSQL_PORT"),
}


def execute_sql_script(cursor, sql_script):
    commands = sql_script.split(";")
    for command in commands:
        stripped_command = command.strip()
        if stripped_command:
            try:
                cursor.execute(stripped_command)
            except mysql.connector.Error as err:
                print(f"Error executing command: {stripped_command}\n{err}")
                raise


def seed_database():
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    instance_dir = os.path.join(project_root, "database")
    if not os.path.exists(instance_dir):
         instance_dir = os.path.join(project_root)

    schema_file = os.path.join(instance_dir, "seed", "schema.sql")
    data_file = os.path.join(instance_dir, "seed", "data.json")

    if not os.path.exists(schema_file):
        print(f"Error: Schema file not found at {schema_file}")
        sys.exit(1)
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at {data_file}")
        sys.exit(1)

    connection = None
    try:
        connection = mysql.connector.connect(
            host=MYSQL_CONFIG["host"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            port=MYSQL_CONFIG["port"],
        )
        cursor = connection.cursor()
        db_name = MYSQL_CONFIG["database"]

        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        cursor.execute(f"CREATE DATABASE {db_name}")
        cursor.execute(f"USE {db_name}")

        with open(schema_file, "r", encoding="utf-8") as f:
            sql_script = f.read()
        execute_sql_script(cursor, sql_script)

        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "content" in data:
            content_data = [
                (item["key"], item["value"]) for item in data["content"]
            ]
            cursor.executemany(
                "INSERT INTO content (`key`, `value`) VALUES (%s, %s)",
                content_data,
            )

        if "users" in data:
            users_to_add = [
                (
                    user["id"],
                    user["username"],
                    user["email"],
                    generate_password_hash(user["password"]),
                    user.get("phone"),
                    user.get("address_line_1"),
                    user.get("address_line_2"),
                    user.get("city"),
                    user.get("province"),
                    user.get("postal_code"),
                    user.get("is_admin", 0),
                    user.get("created_at", datetime.now()),
                )
                for user in data["users"]
            ]
            cursor.executemany(
                """
                INSERT INTO users (
                    id, username, email, password, phone, address_line_1,
                    address_line_2, city, province, postal_code, is_admin,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                users_to_add,
            )

        if "categories" in data:
            categories_data = [
                (item["id"], item["name"]) for item in data["categories"]
            ]
            cursor.executemany(
                "INSERT INTO categories (id, name) VALUES (%s, %s)",
                categories_data,
            )

        if "products" in data:
            products_data = [
                (
                    item["id"],
                    item["name"],
                    item["price"],
                    item.get("discount_price"),
                    item["description"],
                    item["category_id"],
                    item.get("colors"),
                    item.get("popularity", 0),
                    item.get("image_url"),
                    json.dumps(item.get("additional_image_urls", [])),
                    item["stock"],
                    item["has_variants"],
                    item["weight_grams"],
                    item.get("sku"),
                )
                for item in data["products"]
            ]
            cursor.executemany(
                """
                INSERT INTO products (
                    id, name, price, discount_price, description, category_id,
                    colors, popularity, image_url, additional_image_urls, stock,
                    has_variants, weight_grams, sku
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                products_data,
            )

        if "product_variants" in data:
            variants_data = [
                (
                    item["id"],
                    item["product_id"],
                    item["color"],
                    item["size"],
                    item["stock"],
                    item["weight_grams"],
                    item.get("sku"),
                )
                for item in data["product_variants"]
            ]
            cursor.executemany(
                """
                INSERT INTO product_variants (
                    id, product_id, color, size, stock, weight_grams, sku
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                variants_data,
            )

        if "orders" in data:
            orders_data = [
                (
                    item["id"],
                    item["user_id"],
                    item.get("order_date", datetime.now()),
                    item["subtotal"],
                    item.get("discount_amount", 0),
                    item.get("shipping_cost", 0),
                    item["total_amount"],
                    item.get("voucher_code"),
                    item["status"],
                    item.get("payment_method"),
                    item.get("payment_transaction_id"),
                    item.get("shipping_name"),
                    item.get("shipping_phone"),
                    item.get("shipping_address_line_1"),
                    item.get("shipping_address_line_2"),
                    item.get("shipping_city"),
                    item.get("shipping_province"),
                    item.get("shipping_postal_code"),
                    item.get("shipping_email"),
                    item.get("tracking_number"),
                )
                for item in data["orders"]
            ]
            cursor.executemany(
                """
                INSERT INTO orders (
                    id, user_id, order_date, subtotal, discount_amount,
                    shipping_cost, total_amount, voucher_code, status,
                    payment_method, payment_transaction_id, shipping_name,
                    shipping_phone, shipping_address_line_1,
                    shipping_address_line_2, shipping_city,
                    shipping_province, shipping_postal_code,
                    shipping_email, tracking_number
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                """,
                orders_data,
            )

        if "order_items" in data:
            order_items_data = [
                (
                    item["id"],
                    item["order_id"],
                    item["product_id"],
                    item.get("variant_id"),
                    item["quantity"],
                    item["price"],
                    item.get("color_at_order"),
                    item.get("size_at_order"),
                )
                for item in data["order_items"]
            ]
            cursor.executemany(
                """
                INSERT INTO order_items (
                    id, order_id, product_id, variant_id, quantity, price,
                    color_at_order, size_at_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                order_items_data,
            )

        if "reviews" in data:
            reviews_data = [
                (
                    item["id"],
                    item["product_id"],
                    item["user_id"],
                    item["rating"],
                    item["comment"],
                    item.get("created_at", datetime.now()),
                )
                for item in data["reviews"]
            ]
            cursor.executemany(
                """
                INSERT INTO reviews (
                    id, product_id, user_id, rating, comment, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                reviews_data,
            )

        if "vouchers" in data:
            vouchers_data = [
                (
                    item["id"],
                    item["code"],
                    item["type"],
                    item["value"],
                    item.get("max_uses"),
                    item.get("use_count", 0),
                    item.get("min_purchase_amount", 0),
                    item.get("is_active", 1),
                )
                for item in data["vouchers"]
            ]
            cursor.executemany(
                """
                INSERT INTO vouchers
                (id, code, type, value, max_uses, use_count, min_purchase_amount, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                vouchers_data,
            )

        if "user_vouchers" in data:
            user_vouchers_data = [
                (
                    item["user_id"],
                    item["voucher_id"],
                    item.get("status", "available"),
                    item.get("order_id"),
                )
                for item in data["user_vouchers"]
            ]
            cursor.executemany(
                """
                INSERT INTO user_vouchers
                (user_id, voucher_id, status, order_id)
                VALUES (%s, %s, %s, %s)
                """,
                user_vouchers_data,
            )

        if "user_carts" in data:
            user_carts_data = [
                (
                    item["user_id"],
                    item["product_id"],
                    item.get("variant_id"),
                    item["quantity"],
                )
                for item in data["user_carts"]
            ]
            cursor.executemany(
                """
                INSERT INTO user_carts
                (user_id, product_id, variant_id, quantity)
                VALUES (%s, %s, %s, %s)
                """,
                user_carts_data,
            )

        if "memberships" in data:
            memberships_data = [
                (
                    item["id"],
                    item["name"],
                    item["price"],
                    item["period"],
                    item.get("discount_percent", 0),
                    item.get("free_shipping", 0),
                    item.get("description"),
                    item.get("is_active", 1),
                )
                for item in data["memberships"]
            ]
            cursor.executemany(
                """
                INSERT INTO memberships (
                    id, name, price, period, discount_percent,
                    free_shipping, description, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                memberships_data,
            )

        if "user_subscriptions" in data:
            subscriptions_data = [
                (
                    item["id"],
                    item["user_id"],
                    item["membership_id"],
                    item["start_date"],
                    item["end_date"],
                    item["status"],
                )
                for item in data["user_subscriptions"]
            ]
            cursor.executemany(
                """
                INSERT INTO user_subscriptions (
                    id, user_id, membership_id, start_date, end_date, status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                subscriptions_data,
            )

        if "subscription_transactions" in data:
            transactions_data = [
                (
                    item["id"],
                    item["user_id"],
                    item["membership_id"],
                    item["transaction_type"],
                    item["amount"],
                    item.get("transaction_date", datetime.now()),
                    item.get("notes"),
                )
                for item in data["subscription_transactions"]
            ]
            cursor.executemany(
                """
                INSERT INTO subscription_transactions (
                    id, user_id, membership_id, transaction_type,
                    amount, transaction_date, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                transactions_data,
            )

        connection.commit()
        print("Database seeding complete.")

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        if connection:
            connection.rollback()
        sys.exit(1)

    except FileNotFoundError as e:
        print(f"File Error: {e}")
        sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if connection:
            connection.rollback()
        sys.exit(1)

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    seed_database()