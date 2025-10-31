import json
from unittest.mock import patch, MagicMock
from decimal import Decimal

from flask import url_for

from app.exceptions.service_exceptions import InvalidOperationError
from tests.base_test_case import BaseTestCase


class TestPurchaseOrderRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.cancel_service_patch = patch(
            "app.routes.purchase.order_routes.order_cancel_service"
        )
        self.mock_cancel_service = self.cancel_service_patch.start()

        self.get_content_patch = patch(
            "app.routes.purchase.order_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {}

        self.mock_cursor = MagicMock()
        patch.object(self.db_conn, 'cursor', return_value=self.mock_cursor).start()
        
    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_payment_page_get_logged_in_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
        
        mock_order = {
            "id": 1,
            "payment_method": "Virtual Account",
            "status": "Menunggu Pembayaran",
            "total_amount": Decimal("10000"),
            "subtotal": Decimal("10000"),
            "discount_amount": Decimal("0"),
            "shipping_cost": Decimal("0"),
            "voucher_code": None,
            "payment_transaction_id": "sim_123"
        }
        self.mock_cursor.fetchone.return_value = mock_order
        self.mock_cursor.fetchall.return_value = []
        
        response = self.client.get(
            url_for("purchase.payment_page", order_id=1)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Selesaikan Pembayaran", response.data)

    def test_payment_page_get_permission_denied(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
        
        self.mock_cursor.fetchone.return_value = None
        response = self.client.get(
            url_for("purchase.payment_page", order_id=99)
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.location.startswith(url_for("product.index", _external=False))
        )

    def test_order_success_get_success(self):
        response = self.client.get(url_for("purchase.order_success"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pesanan Berhasil!", response.data)

    def test_cancel_order_post_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
        
        self.mock_cancel_service.cancel_user_order.return_value = {
            "success": True,
            "message": "Batal"
        }
        response = self.client.post(
            url_for("purchase.cancel_order", order_id=1),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_cancel_order_post_fail(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
        
        self.mock_cancel_service.cancel_user_order.side_effect = (
            InvalidOperationError("Cannot cancel")
        )
        response = self.client.post(
            url_for("purchase.cancel_order", order_id=1),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])