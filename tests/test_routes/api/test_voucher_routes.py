import json
from unittest.mock import patch

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestApiVoucherRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.discount_service_patch = patch(
            "app.routes.api.voucher_routes.discount_service"
        )
        self.mock_discount_service = self.discount_service_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_apply_voucher_success(self):
        self.mock_discount_service.validate_and_calculate_voucher.return_value = {
            "success": True,
            "discount_amount": 1000,
            "final_total": 9000,
        }
        response = self.client.post(
            url_for("api.apply_voucher"),
            json={"voucher_code": "TEST", "subtotal": 10000},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["discount_amount"], 1000)

    def test_apply_voucher_invalid(self):
        self.mock_discount_service.validate_and_calculate_voucher.return_value = (
            {"success": False, "message": "Voucher tidak valid"}
        )
        response = self.client.post(
            url_for("api.apply_voucher"),
            json={"voucher_code": "INVALID", "subtotal": 10000},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Voucher tidak valid", data["message"])

    def test_apply_voucher_no_data(self):
        response = self.client.post(url_for("api.apply_voucher"), json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Data JSON tidak valid", data["message"])

    def test_apply_voucher_bad_subtotal(self):
        response = self.client.post(
            url_for("api.apply_voucher"),
            json={"voucher_code": "TEST", "subtotal": "abc"},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Format subtotal tidak valid", data["message"])