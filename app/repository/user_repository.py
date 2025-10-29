from mysql.connector.connection import MySQLConnection
from typing import Any, Dict, Optional


class UserRepository:
    
    def find_by_id(
        self, conn: MySQLConnection, user_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_by_username(
        self, conn: MySQLConnection, username: str
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM users WHERE username = %s", (username,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_by_email(
        self, conn: MySQLConnection, email: str
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()
        finally:
            cursor.close()


    def check_existing(
        self, conn: MySQLConnection, username: str, email: str, user_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id FROM users WHERE (username = %s OR email = %s) "
                "AND id != %s",
                (username, email, user_id),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def create(
        self, conn: MySQLConnection,
        username: str, email: str,
        hashed_password: str,
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) "
                "VALUES (%s, %s, %s)",
                (username, email, hashed_password),
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def create_guest(
        self,
        conn: MySQLConnection,
        details: Dict[str, Any],
        hashed_password: str,
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (
                    username, email, password, phone, address_line_1,
                    address_line_2, city, province, postal_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    details["username"],
                    details["email"],
                    hashed_password,
                    details.get("phone"),
                    details.get("address1"),
                    details.get("address2", ""),
                    details.get("city"),
                    details.get("province"),
                    details.get("postal_code"),
                ),
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def update_profile(
        self, conn: MySQLConnection, user_id: int, username: str, email: str
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET username = %s, email = %s WHERE id = %s",
                (username, email, user_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def update_password(
        self, conn: MySQLConnection, user_id: int, hashed_password: str
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET password = %s WHERE id = %s",
                (hashed_password, user_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def update_address(
        self, conn: MySQLConnection, user_id: int, address_data: Dict[str, Any]
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE users
                SET phone = %s, address_line_1 = %s, address_line_2 = %s,
                    city = %s, province = %s, postal_code = %s
                WHERE id = %s
                """,
                (
                    address_data.get("phone"),
                    address_data.get("address1"),
                    address_data.get("address2", ""),
                    address_data.get("city"),
                    address_data.get("province"),
                    address_data.get("postal_code"),
                    user_id,
                ),
            )
            return cursor.rowcount
        finally:
            cursor.close()

user_repository = UserRepository()