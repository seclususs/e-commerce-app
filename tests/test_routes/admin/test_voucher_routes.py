import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.api_exceptions import ValidationError
from tests.base_test_case import BaseTestCase


class TestAdminVoucherRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        
        self.voucher_service_patch = patch(
            "app.routes.admin.voucher_routes.voucher_service"
        )
        self.mock_voucher_service = self.voucher_service_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_vouchers_get_success(self):
        self.mock_voucher_service.get_all_vouchers.return_value = [
            {"id": 1, "code": "TEST10", "type": "PERCENTAGE", "value": 10, "min_purchase_amount": 0, "use_count": 0, "max_uses": 100, "is_active": True}
        ]
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.get(url_for("admin.admin_vouchers"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"TEST10", response.data)

    def test_admin_vouchers_post_add_success(self):
        self.mock_voucher_service.add_voucher.return_value = {
            "success": True,
            "data": {
                "id": 2, 
                "code": "NEW10", 
                "type": "PERCENTAGE", 
                "value": 10, 
                "min_purchase_amount": 0,
                "use_count": 0,
                "max_uses": 100,
                "is_active": True
            },
        }
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(
            url_for("admin.admin_vouchers"),
            data={
                "code": "NEW10",
                "type": "PERCENTAGE",
                "value": 10,
                "min_purchase_amount": 0,
                "max_uses": 100,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)
        self.assertIn(b"NEW10", data["html"].encode('utf-8'))

    def test_admin_vouchers_post_add_validation_error(self):
        self.mock_voucher_service.add_voucher.side_effect = ValidationError(
            "Bad value"
        )
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(
            url_for("admin.admin_vouchers"), data={"code": "BAD"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Bad value", data["message"])

    def test_delete_voucher_post_success(self):
        self.mock_voucher_service.delete_voucher_by_id.return_value = {
            "success": True
        }
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(url_for("admin.delete_voucher", id=1))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_toggle_voucher_post_success(self):
        self.mock_voucher_service.toggle_voucher_status.return_value = {
            "success": True,
            "data": {"id": 1, "is_active": False}
        }
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(url_for("admin.toggle_voucher", id=1))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertFalse(data["data"]["is_active"])