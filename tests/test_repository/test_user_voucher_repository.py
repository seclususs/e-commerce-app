from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.user_voucher_repository import (
    UserVoucherRepository, user_voucher_repository
)


class TestUserVoucherRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        ).start()
        self.repository = UserVoucherRepository()

    def test_singleton_instance(self):
        self.assertIsInstance(user_voucher_repository, UserVoucherRepository)

    def test_create(self):
        self.mock_cursor.lastrowid = 5
        
        result = self.repository.create(self.db_conn, 1, 10)

        self.mock_cursor.execute.assert_called_once_with(
            "\n                INSERT INTO user_vouchers (user_id, voucher_id, status)\n"
            "                VALUES (%s, %s, 'available')\n"
            "                ",
            (1, 10)
        )
        self.assertEqual(result, 5)
        self.mock_cursor.close.assert_called_once()

    def test_find_available_by_user_id(self):
        self.repository.find_available_by_user_id(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once()
        call_args = self.mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("uv.status = 'available'", query)
        self.assertIn("v.is_active = 1", query)
        self.assertEqual(params, (1,))
        self.mock_cursor.close.assert_called_once()

    def test_mark_as_used(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.mark_as_used(self.db_conn, 5, 100)

        self.mock_cursor.execute.assert_called_once_with(
            "\n                UPDATE user_vouchers\n"
            "                SET status = 'used', used_at = CURRENT_TIMESTAMP, order_id = %s\n"
            "                WHERE id = %s AND status = 'available'\n"
            "                ",
            (100, 5)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_user_and_voucher_id(self):
        self.repository.find_by_user_and_voucher_id(self.db_conn, 1, 5)

        self.mock_cursor.execute.assert_called_once()
        call_args = self.mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("v.*", query)
        self.assertIn("uv.id AS user_voucher_id", query)
        self.assertIn("WHERE uv.id = %s AND uv.user_id = %s", query)
        self.assertEqual(params, (5, 1))
        self.mock_cursor.close.assert_called_once()

    def test_find_by_user_and_code(self):
        self.repository.find_by_user_and_code(self.db_conn, 1, "TEST")

        self.mock_cursor.execute.assert_called_once()
        call_args = self.mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("uv.status", query)
        self.assertIn("WHERE uv.user_id = %s AND v.code = %s", query)
        self.assertEqual(params, (1, "TEST"))
        self.mock_cursor.close.assert_called_once()