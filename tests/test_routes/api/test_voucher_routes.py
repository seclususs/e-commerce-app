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
        
        self.voucher_service_patch = patch(
            "app.routes.api.voucher_routes.voucher_service"
        )
        self.mock_voucher_service = self.voucher_service_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_apply_voucher_by_code_success(self):
        self.mock_discount_service.validate_and_calculate_by_code.return_value = {
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
        self.mock_discount_service.validate_and_calculate_by_code.assert_called_once()

    def test_apply_voucher_by_id_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            
        self.mock_discount_service.validate_and_calculate_by_id.return_value = {
            "success": True,
            "discount_amount": 1000,
            "final_total": 9000,
            "user_voucher_id": 5
        }
        response = self.client.post(
            url_for("api.apply_voucher"),
            json={"user_voucher_id": 5, "subtotal": 10000},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["user_voucher_id"], 5)
        self.mock_discount_service.validate_and_calculate_by_id.assert_called_once()

    def test_apply_voucher_invalid(self):
        self.mock_discount_service.validate_and_calculate_by_code.return_value = (
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
        self.assertIn("Subtotal diperlukan.", data["message"])

    def test_apply_voucher_bad_subtotal(self):
        self.mock_discount_service.validate_and_calculate_by_code.side_effect = (
            ValueError("Bad format")
        )
        response = self.client.post(
            url_for("api.apply_voucher"),
            json={"voucher_code": "TEST", "subtotal": "abc"},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Format input tidak valid", data["message"])

    def test_get_my_vouchers_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
        
        self.mock_voucher_service.get_available_vouchers_for_user.return_value = [{"id": 1}]
        response = self.client.get(url_for("api.get_my_vouchers"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["vouchers"]), 1)
        
    def test_get_my_vouchers_not_logged_in(self):
        response = self.client.get(url_for("api.get_my_vouchers"))
        self.assertEqual(response.status_code, 401)

    def test_claim_voucher_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
        
        self.mock_voucher_service.claim_voucher_by_code.return_value = {
            "success": True, "message": "Berhasil"
        }
        response = self.client.post(
            url_for("api.claim_voucher"),
            json={"voucher_code": "TEST"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        
    def test_claim_voucher_fail(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
        
        self.mock_voucher_service.claim_voucher_by_code.return_value = {
            "success": False, "message": "Gagal"
        }
        response = self.client.post(
            url_for("api.claim_voucher"),
            json={"voucher_code": "TEST"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])

    def test_claim_voucher_not_logged_in(self):
        response = self.client.post(
            url_for("api.claim_voucher"),
            json={"voucher_code": "TEST"}
        )
        self.assertEqual(response.status_code, 401)