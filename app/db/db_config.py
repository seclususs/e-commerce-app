import sqlite3
import os
from flask import current_app

def get_db_connection():
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_content():
    conn = get_db_connection()
    content_data = conn.execute('SELECT key, value FROM content').fetchall()
    conn.close()
    return {item['key']: item['value'] for item in content_data}