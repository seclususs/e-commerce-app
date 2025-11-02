from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock
from decimal import Decimal

import mysql.connector

from app.services.orders.voucher_service import VoucherService
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import RecordNotFoundError


class TestVoucherService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_voucher_repo = MagicMock()
        self.mock_user_voucher_repo = MagicMock()
        
        self.voucher_service = VoucherService(
            voucher_repo=self.mock_voucher_repo,
            user_voucher_repo=self.mock_user_voucher_repo
        )
        
        self.voucher_data = {
            "code": "TEST10", "voucher_type": "PERCENTAGE", "value": "10",
            "min_purchase": "50000", "max_uses": "100"
        }
        self.mock_voucher = {"id": 1, "code": "TEST10"}

    def tearDown(self):
        super().tearDown()

    def test_get_active_voucher_by_code_success(self):
        self.mock_voucher_repo.find_active_by_code.return_value = (
            self.mock_voucher
        )
        
        result = self.voucher_service.get_active_voucher_by_code("TEST10")
        
        self.mock_voucher_repo.find_active_by_code.assert_called_once_with(
            self.db_conn, "TEST10"
        )
        self.assertEqual(result, self.mock_voucher)

    def test_get_all_vouchers_success(self):
        mock_vouchers = [{"id": 1, "code": "TEST10"}]
        self.mock_voucher_repo.find_all.return_value = mock_vouchers
        
        result = self.voucher_service.get_all_vouchers()
        
        self.assertEqual(result, mock_vouchers)

    def test_add_voucher_success(self):
        self.mock_voucher_repo.find_by_code.return_value = None
        self.mock_voucher_repo.create.return_value = 1
        new_voucher = {"id": 1, "code": "TEST10"}
        self.mock_voucher_repo.find_by_id.return_value = new_voucher
        
        result = self.voucher_service.add_voucher(**self.voucher_data)
        
        self.mock_voucher_repo.create.assert_called_once_with(
            self.db_conn, "TEST10", "PERCENTAGE", Decimal("10"),
            Decimal("50000"), 100
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], new_voucher)

    def test_add_voucher_code_exists(self):
        self.mock_voucher_repo.find_by_code.return_value = {"id": 99}
        
        result = self.voucher_service.add_voucher(**self.voucher_data)
        
        self.mock_voucher_repo.create.assert_not_called()
        self.assertFalse(result["success"])
        self.assertIn("sudah terdaftar", result["message"])

    def test_add_voucher_validation_error_percentage(self):
        invalid_data = self.voucher_data.copy()
        invalid_data["value"] = "110"
        
        with self.assertRaises(ValidationError):
            self.voucher_service.add_voucher(**invalid_data)

    def test_add_voucher_validation_error_value_type(self):
        invalid_data = self.voucher_data.copy()
        invalid_data["value"] = "abc"
        
        with self.assertRaises(ValidationError):
            self.voucher_service.add_voucher(**invalid_data)

    def test_delete_voucher_by_id_success(self):
        self.mock_voucher_repo.delete.return_value = 1
        
        result = self.voucher_service.delete_voucher_by_id(1)
        
        self.mock_voucher_repo.delete.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertTrue(result["success"])

    def test_delete_voucher_by_id_not_found(self):
        self.mock_voucher_repo.delete.return_value = 0
        
        with self.assertRaises(RecordNotFoundError):
            self.voucher_service.delete_voucher_by_id(1)

    def test_toggle_voucher_status_success(self):
        mock_voucher = {"id": 1, "code": "TEST10", "is_active": True}
        updated_voucher = {"id": 1, "code": "TEST10", "is_active": False}
        self.mock_voucher_repo.find_by_id.side_effect = [
            mock_voucher, updated_voucher
        ]
        
        result = self.voucher_service.toggle_voucher_status(1)
        
        self.mock_voucher_repo.toggle_status.assert_called_once_with(
            self.db_conn, 1, False
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], updated_voucher)

    def test_toggle_voucher_status_not_found(self):
        self.mock_voucher_repo.find_by_id.return_value = None
        
        with self.assertRaises(RecordNotFoundError):
            self.voucher_service.toggle_voucher_status(1)

    def test_claim_voucher_by_code_success(self):
        self.mock_voucher_repo.find_active_by_code.return_value = self.mock_voucher
        self.mock_user_voucher_repo.find_by_user_and_code.return_value = None
        
        result = self.voucher_service.claim_voucher_by_code(1, "TEST10")
        
        self.mock_voucher_repo.find_active_by_code.assert_called_once_with(
            self.db_conn, "TEST10"
        )
        self.mock_user_voucher_repo.find_by_user_and_code.assert_called_once_with(
            self.db_conn, 1, "TEST10"
        )
        self.mock_user_voucher_repo.create.assert_called_once_with(
            self.db_conn, 1, 1
        )
        self.assertTrue(result["success"])

    def test_claim_voucher_by_code_not_found(self):
        self.mock_voucher_repo.find_active_by_code.return_value = None
        
        result = self.voucher_service.claim_voucher_by_code(1, "BADCODE")
        
        self.assertFalse(result["success"])
        self.assertIn("tidak ditemukan", result["message"])

    def test_claim_voucher_by_code_already_claimed(self):
        self.mock_voucher_repo.find_active_by_code.return_value = self.mock_voucher
        self.mock_user_voucher_repo.find_by_user_and_code.return_value = {
            "id": 5, "status": "available"
        }
        
        result = self.voucher_service.claim_voucher_by_code(1, "TEST10")
        
        self.mock_user_voucher_repo.create.assert_not_called()
        self.assertFalse(result["success"])
        self.assertIn("sudah ada di akun Anda", result["message"])

    def test_claim_voucher_by_code_already_used(self):
        self.mock_voucher_repo.find_active_by_code.return_value = self.mock_voucher
        self.mock_user_voucher_repo.find_by_user_and_code.return_value = {
            "id": 5, "status": "used"
        }
        
        result = self.voucher_service.claim_voucher_by_code(1, "TEST10")
        
        self.mock_user_voucher_repo.create.assert_not_called()
        self.assertFalse(result["success"])
        self.assertIn("sudah pernah Anda gunakan", result["message"])

    def test_get_available_vouchers_for_user(self):
        mock_list = [{"id": 1, "code": "TEST10"}]
        (
            self.mock_user_voucher_repo.
            find_available_by_user_id.return_value
        ) = mock_list
        
        result = self.voucher_service.get_available_vouchers_for_user(1)
        
        (
            self.mock_user_voucher_repo.
            find_available_by_user_id.assert_called_once_with(
                self.db_conn, 1
            )
        )
        self.assertEqual(result, mock_list)

    def test_mark_user_voucher_as_used(self):
        self.mock_user_voucher_repo.mark_as_used.return_value = 1
        
        result = self.voucher_service.mark_user_voucher_as_used(
            self.db_conn, 5, 100
        )
        
        self.mock_user_voucher_repo.mark_as_used.assert_called_once_with(
            self.db_conn, 5, 100
        )
        self.assertTrue(result)

    def test_mark_user_voucher_as_used_not_found(self):
        self.mock_user_voucher_repo.mark_as_used.return_value = 0
        
        result = self.voucher_service.mark_user_voucher_as_used(
            self.db_conn, 99, 100
        )
        
        self.assertFalse(result)

    def test_grant_welcome_voucher_success(self):
        self.mock_voucher_repo.find_by_code.return_value = {"id": 20}
        
        result = self.voucher_service.grant_welcome_voucher(self.db_conn, 1)
        
        self.mock_voucher_repo.find_by_code.assert_called_once_with(
            self.db_conn, "WELCOME"
        )
        self.mock_user_voucher_repo.create.assert_called_once_with(
            self.db_conn, 1, 20
        )
        self.assertTrue(result)

    def test_grant_welcome_voucher_not_found(self):
        self.mock_voucher_repo.find_by_code.return_value = None
        
        result = self.voucher_service.grant_welcome_voucher(self.db_conn, 1)
        
        self.mock_user_voucher_repo.create.assert_not_called()
        self.assertFalse(result)

    def test_grant_welcome_voucher_already_exists(self):
        self.mock_voucher_repo.find_by_code.return_value = {"id": 20}
        self.mock_user_voucher_repo.create.side_effect = (
            mysql.connector.IntegrityError()
        )
        
        result = self.voucher_service.grant_welcome_voucher(self.db_conn, 1)
        
        self.assertFalse(result)