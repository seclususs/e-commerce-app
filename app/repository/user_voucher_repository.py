from typing import Any, Dict, List, Optional

from mysql.connector.connection import MySQLConnection


class UserVoucherRepository:

    def find_available_by_user_id(
        self, conn: MySQLConnection, user_id: int
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    uv.id AS user_voucher_id,
                    v.id AS voucher_id,
                    v.code, v.type, v.value,
                    v.min_purchase_amount
                FROM user_vouchers uv
                JOIN vouchers v ON uv.voucher_id = v.id
                WHERE uv.user_id = %s
                  AND uv.status = 'available'
                  AND v.is_active = 1
                  AND (v.end_date IS NULL OR v.end_date > CURRENT_TIMESTAMP)
                  AND (v.start_date IS NULL OR v.start_date <= CURRENT_TIMESTAMP)
                  AND (v.max_uses IS NULL OR v.use_count < v.max_uses)
                """,
                (user_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()

    def find_by_user_and_voucher_id(
        self, conn: MySQLConnection, user_id: int, user_voucher_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    uv.id AS user_voucher_id,
                    uv.status,
                    v.*
                FROM user_vouchers uv
                JOIN vouchers v ON uv.voucher_id = v.id
                WHERE uv.id = %s AND uv.user_id = %s
                """,
                (user_voucher_id, user_id),
            )
            return cursor.fetchone()
        finally:
            cursor.close()

    def find_by_user_and_code(
        self, conn: MySQLConnection, user_id: int, code: str
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    uv.id AS user_voucher_id,
                    uv.status
                FROM user_vouchers uv
                JOIN vouchers v ON uv.voucher_id = v.id
                WHERE uv.user_id = %s AND v.code = %s
                """,
                (user_id, code.upper()),
            )
            return cursor.fetchone()
        finally:
            cursor.close()

    def create(
        self, conn: MySQLConnection, user_id: int, voucher_id: int
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO user_vouchers (user_id, voucher_id, status)
                VALUES (%s, %s, 'available')
                """,
                (user_id, voucher_id),
            )
            return cursor.lastrowid
        finally:
            cursor.close()

    def mark_as_used(
        self,
        conn: MySQLConnection,
        user_voucher_id: int,
        order_id: int,
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE user_vouchers
                SET status = 'used', used_at = CURRENT_TIMESTAMP, order_id = %s
                WHERE id = %s AND status = 'available'
                """,
                (order_id, user_voucher_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()

user_voucher_repository = UserVoucherRepository()