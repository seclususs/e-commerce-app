from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

import mysql.connector

from app.services.orders.checkout_validation_service import (
    CheckoutValidationService
)
from app.exceptions.database_exceptions import DatabaseException


class TestCheckoutValidationService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_order_repo = MagicMock()
        self.mock_user_repo = MagicMock()
        
        self.checkout_validation_service = CheckoutValidationService(
            order_repo=self.mock_order_repo,
            user_repo=self.mock_user_repo
        )

    def tearDown(self):
        super().tearDown()

    def test_check_pending_order_found(self):
        mock_order = {"id": 1}
        self.mock_order_repo.find_pending_by_user_id.return_value = mock_order
        
        result = self.checkout_validation_service.check_pending_order(1)

        self.mock_order_repo.find_pending_by_user_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertEqual(result, mock_order)

    def test_check_pending_order_not_found(self):
        self.mock_order_repo.find_pending_by_user_id.return_value = None
        
        result = self.checkout_validation_service.check_pending_order(1)
        
        self.assertIsNone(result)

    def test_check_pending_order_db_error(self):
        self.mock_order_repo.find_pending_by_user_id.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.checkout_validation_service.check_pending_order(1)

    def test_validate_user_address_valid(self):
        user = {
            "phone": "123", "address_line_1": "Street", "city": "City",
            "province": "Prov", "postal_code": "12345"
        }
        self.assertTrue(
            self.checkout_validation_service.validate_user_address(user)
        )

    def test_validate_user_address_invalid_missing_field(self):
        user = {
            "phone": "123", "address_line_1": "Street", "city": "City",
            "province": "Prov"
        }
        self.assertFalse(
            self.checkout_validation_service.validate_user_address(user)
        )

    def test_validate_user_address_invalid_none_user(self):
        self.assertFalse(
            self.checkout_validation_service.validate_user_address(None)
        )

    def test_check_guest_email_exists_true(self):
        self.mock_user_repo.find_by_email.return_value = {"id": 1}
        
        result = self.checkout_validation_service.check_guest_email_exists(
            "exists@mail.com"
        )
        
        self.mock_user_repo.find_by_email.assert_called_once_with(
            self.db_conn, "exists@mail.com"
        )
        self.assertTrue(result)

    def test_check_guest_email_exists_false(self):
        self.mock_user_repo.find_by_email.return_value = None
        
        result = self.checkout_validation_service.check_guest_email_exists(
            "new@mail.com"
        )
        
        self.assertFalse(result)

    def test_check_guest_email_exists_db_error(self):
        self.mock_user_repo.find_by_email.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.checkout_validation_service.check_guest_email_exists(
                "any@mail.com"
            )