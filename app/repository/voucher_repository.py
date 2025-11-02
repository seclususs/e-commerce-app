from mysql.connector.connection import MySQLConnection
from typing import Any, Dict, List, Optional
from decimal import Decimal


class VoucherRepository:

    def find_active_by_code(
        self, conn: MySQLConnection, code: str
    ) -> Optional[Dict[str, Any]]:
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM vouchers WHERE UPPER(code) = %s "
                "AND is_active = 1",
                (code.upper().strip(),),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_by_code(
        self, conn: MySQLConnection, code: str
    ) -> Optional[Dict[str, Any]]:
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id FROM vouchers WHERE UPPER(code) = %s",
                (code.upper().strip(),),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_all(self, conn: MySQLConnection) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM vouchers ORDER BY id DESC")
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_by_id(
        self, conn: MySQLConnection, voucher_id: int
    ) -> Optional[Dict[str, Any]]:
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM vouchers WHERE id = %s", (voucher_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def create(
        self, conn: MySQLConnection,
        code: str, voucher_type: str,
        value: Decimal, min_purchase: Decimal,
        max_uses: Optional[int],
    ) -> int:
        
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO vouchers
                (code, type, value, min_purchase_amount, max_uses)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (code, voucher_type, value, min_purchase, max_uses),
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def delete(self, conn: MySQLConnection, voucher_id: int) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM vouchers WHERE id = %s", (voucher_id,)
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def toggle_status(
        self, conn: MySQLConnection, voucher_id: int, new_status: bool
    ) -> int:
        
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE vouchers SET is_active = %s WHERE id = %s",
                (new_status, voucher_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def increment_use_count(self, conn: MySQLConnection, code: str) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE vouchers SET use_count = use_count + 1 WHERE code = %s",
                (code.upper(),),
            )
            return cursor.rowcount
        finally:
            cursor.close()

voucher_repository = VoucherRepository()