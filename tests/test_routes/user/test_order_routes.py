import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestUserOrderRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.get_content_patch = patch(
            "app.routes.user.order_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {"app_name": "Test App"}
        self.mock_cursor = MagicMock()
        patch.object(self.db_conn, 'cursor', return_value=self.mock_cursor).start()
        
        self.mock_order = {
            "id": 1, 
            "user_id": 1,
            "order_date": datetime(2025, 1, 1, 12, 0, 0),
            "status": "Dikirim",
            "tracking_number": "RESI123",
            "subtotal": Decimal("100000.00"),
            "discount_amount": Decimal("10000.00"),
            "voucher_code": "TEST10",
            "shipping_cost": Decimal("5000.00"),
            "total_amount": Decimal("95000.00")
        }
        self.mock_items = [
            {"id": 1, "product_id": 1, "name": "Produk A", "size_at_order": "M", "quantity": 1, "price": 100000}
        ]
        self.mock_history = [
            {"id": 1, "status": "Dikirim", "timestamp": datetime(2025, 1, 2, 9, 0, 0), "notes": "Paket diserahkan ke kurir"},
            {"id": 2, "status": "Diproses", "timestamp": datetime(2025, 1, 1, 14, 0, 0), "notes": "Pesanan dikemas"}
        ]
        
    def tearDown(self):
        self.mock_cursor.reset_mock()
        patch.stopall()
        super().tearDown()

    def test_track_order_get_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
        
        self.mock_cursor.fetchone.return_value = self.mock_order
        self.mock_cursor.fetchall.side_effect = [self.mock_items, self.mock_history]

        response = self.client.get(url_for("user.track_order", order_id=1))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pelacakan Pesanan", response.data)
        self.assertIn(b"RESI123", response.data)
        self.assertIn(b"Produk A", response.data)
        self.assertIn(b"Paket diserahkan ke kurir", response.data)


    def test_track_order_get_ajax_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        self.mock_cursor.fetchone.return_value = self.mock_order
        self.mock_cursor.fetchall.side_effect = [self.mock_items, self.mock_history]

        response = self.client.get(
            url_for("user.track_order", order_id=1),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)
        self.assertIn("RESI123", data["html"])

    def test_track_order_get_not_found(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        self.mock_cursor.fetchone.return_value = None
        response = self.client.get(
            url_for("user.track_order", order_id=99),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Pesanan tidak ditemukan", data["message"])

    def test_track_order_not_logged_in(self):
        response = self.client.get(url_for("user.track_order", order_id=1))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(url_for("auth.login", _external=False)))