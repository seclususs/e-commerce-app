from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock
from decimal import Decimal

from app.services.orders.voucher_service import VoucherService
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import RecordNotFoundError


class TestVoucherService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_voucher_repo = MagicMock()
        
        self.voucher_service = VoucherService(
            voucher_repo=self.mock_voucher_repo
        )
        
        self.voucher_data = {
            "code": "TEST10", "voucher_type": "PERCENTAGE", "value": "10",
            "min_purchase": "50000", "max_uses": "100"
        }

    def tearDown(self):
        super().tearDown()

    def test_get_active_voucher_by_code_success(self):
        mock_voucher = {"id": 1, "code": "TEST10"}
        self.mock_voucher_repo.find_active_by_code.return_value = mock_voucher
        
        result = self.voucher_service.get_active_voucher_by_code("TEST10")
        
        self.mock_voucher_repo.find_active_by_code.assert_called_once_with(
            self.db_conn, "TEST10"
        )
        self.assertEqual(result, mock_voucher)

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