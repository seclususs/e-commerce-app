from decimal import Decimal
from unittest.mock import MagicMock, call, patch

from tests.base_test_case import BaseTestCase
from app.repository.voucher_repository import (
    VoucherRepository, voucher_repository
)


class TestVoucherRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        ).start()
        self.repository = VoucherRepository()

    def test_singleton_instance(self):
        self.assertIsInstance(voucher_repository, VoucherRepository)

    def test_find_active_by_code(self):
        mock_result = {"id": 1, "code": "TEST"}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_active_by_code(self.db_conn, " test ")

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM vouchers WHERE UPPER(code) = %s "
            "AND is_active = 1",
            ("TEST",)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_code(self):
        self.repository.find_by_code(self.db_conn, " test ")

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT id FROM vouchers WHERE UPPER(code) = %s",
            ("TEST",)
        )
        self.mock_cursor.close.assert_called_once()

    def test_find_all(self):
        self.repository.find_all(self.db_conn)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM vouchers ORDER BY id DESC"
        )
        self.mock_cursor.close.assert_called_once()

    def test_find_by_id(self):
        self.repository.find_by_id(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM vouchers WHERE id = %s", (1,)
        )
        self.mock_cursor.close.assert_called_once()

    def test_create(self):
        self.mock_cursor.lastrowid = 5
        
        result = self.repository.create(
            self.db_conn, "NEW", "PERCENTAGE", Decimal("10"),
            Decimal("50000"), 100
        )

        self.mock_cursor.execute.assert_called_once_with(
            "\n                INSERT INTO vouchers\n"
            "                (code, type, value, "
            "min_purchase_amount, max_uses)\n"
            "                VALUES (%s, %s, %s, %s, %s)\n"
            "                ",
            ("NEW", "PERCENTAGE", Decimal("10"), Decimal("50000"), 100)
        )
        self.assertEqual(result, 5)
        self.mock_cursor.close.assert_called_once()

    def test_delete(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.delete(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM vouchers WHERE id = %s", (1,)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_toggle_status(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.toggle_status(self.db_conn, 1, False)

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE vouchers SET is_active = %s WHERE id = %s",
            (False, 1)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_increment_use_count(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.increment_use_count(self.db_conn, "test")

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE vouchers SET use_count = use_count + 1 WHERE code = %s",
            ("TEST",)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()