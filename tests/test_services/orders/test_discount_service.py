from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.services.orders.discount_service import DiscountService
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException


class TestDiscountService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_voucher_service = MagicMock()

        self.patch_voucher_svc = patch(
            'app.services.orders.discount_service.voucher_service',
            self.mock_voucher_service
        )
        
        self.patch_voucher_svc.start()
        
        self.discount_service = DiscountService()
        
        self.mock_voucher_percent = {
            "id": 1, "code": "TENOFF", "type": "PERCENTAGE", "value": 10,
            "min_purchase_amount": 50000, "max_uses": None, "use_count": 0,
            "start_date": None, "end_date": None, "is_active": True
        }
        self.mock_voucher_fixed = {
            "id": 2, "code": "DISKON5K", "type": "FIXED_AMOUNT", "value": 5000,
            "min_purchase_amount": 0, "max_uses": 100, "use_count": 50,
            "start_date": None, "end_date": None, "is_active": True
        }

    def tearDown(self):
        self.patch_voucher_svc.stop()
        super().tearDown()

    def test_validate_and_calculate_by_code_success(self):
        self.mock_voucher_service.get_active_voucher_by_code.return_value = (
            self.mock_voucher_percent
        )
        
        result = self.discount_service.validate_and_calculate_by_code(
            "TENOFF", 100000
        )
        
        self.mock_voucher_service.get_active_voucher_by_code.assert_called_once_with(
            "TENOFF"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["discount_amount"], 10000.0)
        self.assertEqual(result["final_total"], 90000.0)
        self.assertEqual(result["code"], "TENOFF")

    def test_validate_and_calculate_by_id_success(self):
        mock_user_voucher = {
            **self.mock_voucher_fixed,
            "user_voucher_id": 5,
            "status": "available"
        }
        self.mock_voucher_service.get_user_voucher_by_id.return_value = (
            mock_user_voucher
        )
        
        result = self.discount_service.validate_and_calculate_by_id(
            1, 5, 30000
        )
        
        self.mock_voucher_service.get_user_voucher_by_id.assert_called_once_with(
            1, 5
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["discount_amount"], 5000.0)
        self.assertEqual(result["final_total"], 25000.0)
        self.assertEqual(result["user_voucher_id"], 5)
        self.assertEqual(result["code"], "DISKON5K")

    def test_validate_and_calculate_by_code_not_found(self):
        self.mock_voucher_service.get_active_voucher_by_code.return_value = None
        
        result = self.discount_service.validate_and_calculate_by_code(
            "INVALID", 100000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("tidak valid", result["message"])

    def test_validate_and_calculate_by_id_not_found(self):
        self.mock_voucher_service.get_user_voucher_by_id.return_value = None
        
        result = self.discount_service.validate_and_calculate_by_id(
            1, 99, 100000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("tidak ditemukan", result["message"])

    def test_validate_and_calculate_by_id_not_available(self):
        mock_user_voucher = {
            **self.mock_voucher_fixed,
            "user_voucher_id": 5,
            "status": "used"
        }
        self.mock_voucher_service.get_user_voucher_by_id.return_value = (
            mock_user_voucher
        )
        
        result = self.discount_service.validate_and_calculate_by_id(
            1, 5, 30000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("sudah Anda gunakan", result["message"])

    def test_validate_and_calculate_by_code_below_min_purchase(self):
        self.mock_voucher_service.get_active_voucher_by_code.return_value = (
            self.mock_voucher_percent
        )
        
        result = self.discount_service.validate_and_calculate_by_code(
            "TENOFF", 40000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("Minimal pembelian", result["message"])

    def test_validate_and_calculate_by_id_below_min_purchase(self):
        mock_user_voucher = {
            **self.mock_voucher_percent,
            "user_voucher_id": 5,
            "status": "available"
        }
        self.mock_voucher_service.get_user_voucher_by_id.return_value = (
            mock_user_voucher
        )
        
        result = self.discount_service.validate_and_calculate_by_id(
            1, 5, 40000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("Minimal pembelian", result["message"])

    def test_validate_and_calculate_by_code_max_uses_reached(self):
        voucher_maxed = self.mock_voucher_fixed.copy()
        voucher_maxed["use_count"] = 100
        self.mock_voucher_service.get_active_voucher_by_code.return_value = (
            voucher_maxed
        )
        
        result = self.discount_service.validate_and_calculate_by_code(
            "DISKON5K", 30000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("habis digunakan", result["message"])

    def test_validate_and_calculate_by_code_expired(self):
        voucher_expired = self.mock_voucher_percent.copy()
        voucher_expired["end_date"] = datetime.now() - timedelta(days=1)
        self.mock_voucher_service.get_active_voucher_by_code.return_value = (
            voucher_expired
        )
        
        result = self.discount_service.validate_and_calculate_by_code(
            "TENOFF", 100000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("kedaluwarsa", result["message"])

    def test_validate_and_calculate_invalid_subtotal_format(self):
        with self.assertRaises(ValidationError):
            self.discount_service.validate_and_calculate_by_code(
                "TENOFF", "abc"
            )

    def test_validate_and_calculate_by_code_db_error(self):
        self.mock_voucher_service.get_active_voucher_by_code.side_effect = (
            DatabaseException("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.discount_service.validate_and_calculate_by_code(
                "TENOFF", 100000
            )

    def test_validate_and_calculate_by_id_db_error(self):
        self.mock_voucher_service.get_user_voucher_by_id.side_effect = (
            DatabaseException("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.discount_service.validate_and_calculate_by_id(
                1, 5, 100000
            )