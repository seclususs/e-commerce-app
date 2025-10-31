import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.environ.get("MYSQL_HOST")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
MYSQL_PORT = os.environ.get("MYSQL_PORT")

TEST_DB_NAME = "ecommerce_db_test"

def execute_sql_script(cursor, sql_script):
    """Mengeksekusi skrip SQL multi-pernyataan."""
    commands = sql_script.split(";")
    for command in commands:
        stripped_command = command.strip()
        if stripped_command:
            try:
                cursor.execute(stripped_command)
            except mysql.connector.Error as err:
                if err.errno not in (1008, 1051): 
                    print(f"Error executing command: {stripped_command}\n{err}")
                    raise

def seed_test_database():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(base_dir,"database","seed", "schema.sql")
    if not os.path.exists(schema_file):
        print(f"Error: Schema file not found at {schema_file}")
        return

    connection = None
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            autocommit=True
        )
        cursor = connection.cursor()
        
        print(f"--- TEST DATABASE SETUP ---")
        print(f"Dropping TEST database '{TEST_DB_NAME}' if exists...")
        cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")

        print(f"Creating TEST database '{TEST_DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {TEST_DB_NAME}")
        cursor.execute(f"USE {TEST_DB_NAME}")
        print(f"TEST Database '{TEST_DB_NAME}' selected.")

        print("\nMembaca dan menjalankan schema.sql...")
        with open(schema_file, "r") as f:
            sql_script = f.read()
        
        execute_sql_script(cursor, sql_script)
        print("Skema tabel berhasil dibuat untuk database TES.")
        
        print("\nSetup database TES selesai.")

    except mysql.connector.Error as err:
        print(f"Terjadi kesalahan MySQL: {err}")
    except Exception as e:
        print(f"Terjadi kesalahan tak terduga: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("Koneksi database TES ditutup.")

if __name__ == "__main__":
    seed_test_database()