import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from flask import url_for

from app.exceptions.database_exceptions import RecordNotFoundError
from app.exceptions.service_exceptions import InvalidOperationError
from tests.base_test_case import BaseTestCase


class TestAdminOrderRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        
        self.order_query_patch = patch(
            "app.routes.admin.order_routes.order_query_service"
        )
        self.mock_order_query_service = self.order_query_patch.start()

        self.order_update_patch = patch(
            "app.routes.admin.order_routes.order_update_service"
        )
        self.mock_order_update_service = self.order_update_patch.start()
        
        self.get_content_patch = patch("app.routes.admin.order_routes.get_content")
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {}

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_orders_get_success(self):
        self.mock_order_query_service.get_filtered_admin_orders.return_value = [
            {"id": 1, "shipping_name": "Test User", "order_date": MagicMock(), "total_amount": 1000, "status": "Dikirim"}
        ]
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.get(url_for("admin.admin_orders"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test User", response.data)

    def test_admin_order_detail_get_success(self):
        self.mock_order_query_service.get_order_details_for_admin.return_value = (
            {
                "id": 1, 
                "shipping_name": "Test User", 
                "customer_name": "Test User", 
                "email": "a@b.c", 
                "order_date": datetime.now(),
                "status": "Tes", 
                "total_amount": 100,
                "tracking_number": "123",
                "shipping_phone": "08123",
                "shipping_address_line_1": "Jl. Tes",
                "shipping_address_line_2": "",
                "shipping_city": "Kota",
                "shipping_province": "Prov",
                "shipping_postal_code": "12345",
                "payment_method": "COD"
            },
            [{"name": "Test Product", "price": 100, "quantity": 1, "size_at_order": "M"}],
        )

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True
            
        response = self.client.get(url_for("admin.admin_order_detail", id=1))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test User", response.data)
        self.assertIn(b"Test Product", response.data)

    def test_admin_order_detail_get_not_found(self):
        self.mock_order_query_service.get_order_details_for_admin.side_effect = (
            RecordNotFoundError("Not found")
        )

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.get(
            url_for("admin.admin_order_detail", id=99)
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.location.startswith(url_for("admin.admin_orders", _external=False))
        )

    def test_update_order_status_post_success(self):
        self.mock_order_update_service.update_order_status_and_tracking.return_value = {
            "success": True,
            "data": {"status": "Dikirim", "status_class": "badge-info", "tracking_number": "123"},
        }

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(
            url_for("admin.update_order_status", id=1),
            data={"status": "Dikirim", "tracking_number": "123"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["status"], "Dikirim")

    def test_update_order_status_post_fail(self):
        self.mock_order_update_service.update_order_status_and_tracking.side_effect = (
            InvalidOperationError("Cannot update")
        )

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(
            url_for("admin.update_order_status", id=1),
            data={"status": "Selesai"},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Cannot update", data["message"])