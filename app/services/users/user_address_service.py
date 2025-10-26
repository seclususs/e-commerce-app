import logging
from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class UserAddressService:

    def update_user_address(
        self,
        user_id: int,
        address_data: Dict[str, Any],
        conn: Optional[MySQLConnection] = None,
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba memperbarui alamat untuk pengguna ID: {user_id}. "
            f"Data: {address_data}"
        )

        is_external_conn: bool = conn is not None
        cursor: Optional[Any] = None

        if not is_external_conn:
            logger.debug("Membuat koneksi DB baru untuk update_user_address.")
            conn = get_db_connection()

        try:
            cursor = conn.cursor()

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

            if not is_external_conn:
                conn.commit()

            logger.info(
                f"Alamat berhasil diperbarui untuk pengguna ID: {user_id}. "
                f"Baris terpengaruh: {cursor.rowcount}"
            )

            return {"success": True, "message": "Alamat berhasil diperbarui."}
        
        except mysql.connector.Error as db_err:
            if not is_external_conn and conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui alamat untuk "
                f"pengguna ID {user_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memperbarui alamat: {db_err}"
            )
        
        except Exception as e:
            if not is_external_conn and conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat memperbarui alamat untuk "
                f"pengguna ID {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal memperbarui alamat: {e}")

        finally:
            if cursor:
                cursor.close()

            if not is_external_conn and conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Koneksi DB ditutup untuk update_user_address "
                    f"(ID: {user_id})."
                )

            elif is_external_conn:
                logger.debug(
                    f"Kursor ditutup untuk update_user_address "
                    f"(ID: {user_id}, koneksi eksternal)."
                )

user_address_service = UserAddressService()