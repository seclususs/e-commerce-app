from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.order_repository import (
    OrderRepository, order_repository
)


class TestOrderRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        self.cursor_patch = patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        )
        self.cursor_patch.start()
        self.repository = OrderRepository()

    def tearDown(self):
        self.cursor_patch.stop()
        super().tearDown()

    def test_singleton_instance(self):
        self.assertIsInstance(order_repository, OrderRepository)

    def test_find_pending_by_user_id(self):
        mock_result = {"id": 100}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_pending_by_user_id(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once()
        self.assertIn("status = 'Menunggu Pembayaran'",
                      self.mock_cursor.execute.call_args[0][0])
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_transaction_id(self):
        mock_result = {"id": 100, "status": "Menunggu Pembayaran"}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_by_transaction_id(
            self.db_conn, "TRANS123"
        )

        self.mock_cursor.execute.assert_called_once()
        self.assertIn("payment_transaction_id = %s",
                      self.mock_cursor.execute.call_args[0][0])
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_update_status(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.update_status(
            self.db_conn, 100, "Diproses"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE orders SET status = %s WHERE id = %s",
            ("Diproses", 100)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_update_status_and_notes(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.update_status_and_notes(
            self.db_conn, 100, "Dibatalkan", "Stok habis"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE orders SET status = %s, notes = %s WHERE id = %s",
            ("Dibatalkan", "Stok habis", 100)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_id_and_user_id_for_update(self):
        mock_result = {"id": 100, "status": "Menunggu Pembayaran"}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_by_id_and_user_id_for_update(
            self.db_conn, 100, 1
        )

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM orders WHERE id = %s AND user_id = %s FOR UPDATE",
            (100, 1)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_id_for_update(self):
        mock_result = {"status": "Diproses", "tracking_number": None}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_by_id_for_update(self.db_conn, 100)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT status, tracking_number FROM orders "
            "WHERE id = %s FOR UPDATE",
            (100,)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_filtered_admin_all_filters(self):
        self.repository.find_filtered_admin(
            self.db_conn, "Dikirim", "2025-01-01", "2025-01-31", "TestUser"
        )

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("o.status = %s", query)
        self.assertIn("DATE(o.order_date) >= %s", query)
        self.assertIn("DATE(o.order_date) <= %s", query)
        self.assertIn("o.shipping_name LIKE %s", query)
        self.assertEqual(
            params,
            ("Dikirim", "2025-01-01", "2025-01-31",
             "%TestUser%", "%TestUser%", "%TestUser%")
        )
        self.mock_cursor.close.assert_called_once()

    def test_find_filtered_admin_no_filters(self):
        self.repository.find_filtered_admin(
            self.db_conn, None, None, None, None
        )

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertNotIn("status", query)
        self.assertNotIn("LIKE", query)
        self.assertIn("ORDER BY o.order_date DESC", query) 
        self.assertEqual(params, ())
        self.mock_cursor.close.assert_called_once()

    def test_create(self):
        shipping_details = {
            "name": "Test User", "phone": "123", "address1": "Jalan 1",
            "city": "Kota", "province": "Prov", "postal_code": "12345",
            "email": "a@b.c"
        }
        self.mock_cursor.lastrowid = 101
        
        result = self.repository.create(
            self.db_conn, 1, Decimal("100"), Decimal("10"), Decimal("5"),
            Decimal("95"), "VOUCHER", "COD", None, shipping_details
        )

        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, 101)
        self.mock_cursor.close.assert_called_once()

    def test_find_expired_pending_orders(self):
        mock_result = [{"id": 1}, {"id": 2}]
        self.mock_cursor.fetchall.return_value = mock_result
        expiration_time = datetime(2025, 1, 1, 12, 0, 0)
        
        result = self.repository.find_expired_pending_orders(
            self.db_conn, expiration_time
        )

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT id FROM orders "
            "WHERE status = 'Menunggu Pembayaran' AND order_date < %s",
            (expiration_time,)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_bulk_update_status(self):
        self.mock_cursor.rowcount = 2
        order_ids = [1, 2]
        
        result = self.repository.bulk_update_status(
            self.db_conn, order_ids, "Dibatalkan"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE orders SET status = %s WHERE id IN (%s, %s)",
            ("Dibatalkan", 1, 2)
        )
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()