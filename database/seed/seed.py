import json
import os

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
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    instance_dir = os.path.join(project_root, "database")
    schema_file = os.path.join(instance_dir, "seed", "schema.sql")
    data_file = os.path.join(instance_dir, "seed", "data.json")

    if not os.path.exists(schema_file):
        print(f"Error: Schema file not found at {schema_file}")
        return

    if not os.path.exists(data_file):
        print(f"Error: Data file not found at {data_file}")
        return

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

        print(f"Dropping database '{db_name}' if exists...")
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")

        print(f"Creating database '{db_name}'...")
        cursor.execute(f"CREATE DATABASE {db_name}")
        cursor.execute(f"USE {db_name}")
        print(f"Database '{db_name}' selected.")

        print("\nMembaca dan menjalankan skema SQL...")
        with open(schema_file, "r") as f:
            sql_script = f.read()
        execute_sql_script(cursor, sql_script)
        print("Skema tabel berhasil dibuat.")

        print("\nMembaca data JSON...")
        with open(data_file, "r") as f:
            data = json.load(f)
        print("Data JSON berhasil dibaca.")

        print("\nMemasukkan data awal...")

        # Content
        if "content" in data:
            content_data = [(item["key"], item["value"]) for item in data["content"]]
            cursor.executemany(
                "INSERT INTO content (`key`, `value`) VALUES (%s, %s)", content_data
            )
            connection.commit()
            print(f"- Data 'content' ({len(content_data)} baris) berhasil dimasukkan.")

        # Users
        if "users" in data:
            users_to_add = [
                (
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
                )
                for user in data["users"]
            ]

            reg_count = data.get("regular_users_count", 0)
            reg_pass = data.get("regular_user_password", "password123")
            hashed_reg_pass = generate_password_hash(reg_pass)

            for i in range(1, reg_count + 1):
                users_to_add.append(
                    (
                        f"user{i}",
                        f"user{i}@example.com",
                        hashed_reg_pass,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        0,
                    )
                )

            cursor.executemany(
                """
                INSERT INTO users (
                    username, email, password, phone, address_line_1, address_line_2,
                    city, province, postal_code, is_admin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                users_to_add,
            )
            connection.commit()
            print(f"- Data 'users' ({len(users_to_add)} baris) berhasil dimasukkan.")

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


if __name__ == "__main__":
    seed_database()