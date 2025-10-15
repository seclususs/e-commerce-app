import sqlite3
import os

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_content():
    conn = get_db_connection()
    content_data = conn.execute('SELECT key, value FROM content').fetchall()
    conn.close()
    return {item['key']: item['value'] for item in content_data}