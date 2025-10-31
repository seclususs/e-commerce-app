from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

import mysql.connector

from app.services.utils.validation_service import ValidationService
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError


class TestValidationService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_user_repo = MagicMock()
        
        self.validation_service = ValidationService(
            user_repo=self.mock_user_repo
        )

    def tearDown(self):
        super().tearDown()

    def test_validate_username_availability_available(self):
        self.mock_user_repo.find_by_username.return_value = None
        
        is_available, message = (
            self.validation_service.validate_username_availability("new_user")
        )
        
        self.mock_user_repo.find_by_username.assert_called_once_with(
            self.db_conn, "new_user"
        )
        self.assertTrue(is_available)
        self.assertEqual(message, "Username tersedia.")

    def test_validate_username_availability_taken(self):
        self.mock_user_repo.find_by_username.return_value = {"id": 1}
        
        is_available, message = (
            self.validation_service.validate_username_availability("taken_user")
        )
        
        self.mock_user_repo.find_by_username.assert_called_once_with(
            self.db_conn, "taken_user"
        )
        self.assertFalse(is_available)
        self.assertEqual(message, "Username sudah digunakan.")

    def test_validate_username_availability_db_error(self):
        self.mock_user_repo.find_by_username.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.validation_service.validate_username_availability("any_user")

    def test_validate_username_availability_service_error(self):
        self.mock_user_repo.find_by_username.side_effect = (
            Exception("Service Error")
        )
        
        with self.assertRaises(ServiceLogicError):
            self.validation_service.validate_username_availability("any_user")

    def test_validate_email_availability_available(self):
        self.mock_user_repo.find_by_email.return_value = None
        
        is_available, message = (
            self.validation_service.validate_email_availability("new@mail.com")
        )
        
        self.mock_user_repo.find_by_email.assert_called_once_with(
            self.db_conn, "new@mail.com"
        )
        self.assertTrue(is_available)
        self.assertEqual(message, "Email tersedia.")

    def test_validate_email_availability_taken(self):
        self.mock_user_repo.find_by_email.return_value = {"id": 1}
        
        is_available, message = (
            self.validation_service.validate_email_availability("taken@mail.com")
        )
        
        self.mock_user_repo.find_by_email.assert_called_once_with(
            self.db_conn, "taken@mail.com"
        )
        self.assertFalse(is_available)
        self.assertEqual(message, "Email sudah terdaftar.")