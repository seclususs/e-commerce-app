from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from mysql.connector.connection import MySQLConnection


class MembershipRepository:

    def find_active_subscription_by_user_id(
        self, conn: MySQLConnection, user_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT
                    m.id AS membership_id,
                    m.name,
                    m.price,
                    m.period,
                    m.discount_percent,
                    m.free_shipping,
                    m.description,
                    us.id AS user_subscription_id,
                    us.start_date,
                    us.end_date,
                    us.status
                FROM user_subscriptions us
                JOIN memberships m ON us.membership_id = m.id
                WHERE us.user_id = %s
                  AND us.status = 'active'
                  AND us.end_date > CURRENT_TIMESTAMP
                LIMIT 1
            """
            cursor.execute(query, (user_id,))
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_membership_by_id(
        self, conn: MySQLConnection, membership_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM memberships WHERE id = %s", (membership_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_all_active_memberships(
        self, conn: MySQLConnection
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM memberships WHERE is_active = 1 "
                "ORDER BY price"
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def create_subscription(
        self, conn: MySQLConnection, user_id: int, membership_id: int,
        start_date: datetime, end_date: datetime, status: str
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO user_subscriptions
                (user_id, membership_id, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, membership_id, start_date, end_date, status)
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def update_subscription(
        self, conn: MySQLConnection, user_subscription_id: int,
        membership_id: int, start_date: datetime,
        end_date: datetime, status: str
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE user_subscriptions
                SET membership_id = %s, start_date = %s, end_date = %s,
                    status = %s
                WHERE id = %s
                """,
                (membership_id, start_date, end_date, status,
                 user_subscription_id)
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def create_transaction(
        self, conn: MySQLConnection, user_id: int, membership_id: int,
        transaction_type: str, amount: Decimal, notes: Optional[str] = None
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO subscription_transactions
                (user_id, membership_id, transaction_type, amount, notes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, membership_id, transaction_type, amount, notes)
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def create_membership(
        self, conn: MySQLConnection, data: Dict[str, Any]
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO memberships
                (name, price, period, discount_percent, free_shipping,
                 description, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    data['name'], data['price'], data['period'],
                    data.get('discount_percent', 0),
                    data.get('free_shipping', 0),
                    data.get('description'),
                    data.get('is_active', 1)
                )
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def update_membership(
        self, conn: MySQLConnection, membership_id: int, data: Dict[str, Any]
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE memberships
                SET name = %s, price = %s, period = %s,
                    discount_percent = %s, free_shipping = %s,
                    description = %s, is_active = %s
                WHERE id = %s
                """,
                (
                    data['name'], data['price'], data['period'],
                    data.get('discount_percent', 0),
                    data.get('free_shipping', 0),
                    data.get('description'),
                    data.get('is_active', 1),
                    membership_id
                )
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def find_all_memberships(
        self, conn: MySQLConnection
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM memberships ORDER BY price")
            return cursor.fetchall()
        finally:
            cursor.close()

    def delete_membership(self, conn: MySQLConnection, membership_id: int) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM memberships WHERE id = %s", (membership_id,)
            )
            return cursor.rowcount
        finally:
            cursor.close()

membership_repository = MembershipRepository()