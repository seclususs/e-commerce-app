from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch
import uuid

import mysql.connector

from app.services.auth.password_reset_service import PasswordResetService
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError


class TestPasswordResetService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_user_repo = MagicMock()
        
        self.patch_uuid = patch(
            'app.services.auth.password_reset_service.uuid.uuid4'
        )
        self.patch_logger_info = patch(
            'app.services.auth.password_reset_service.logger.info'
        )
        
        self.mock_uuid = self.patch_uuid.start()
        self.mock_uuid.return_value = uuid.UUID('12345678123456781234567812345678')
        self.mock_logger_info = self.patch_logger_info.start()
        
        self.password_reset_service = PasswordResetService(
            user_repo=self.mock_user_repo
        )
        
        self.email = "test@example.com"
        self.mock_user = {"id": 1, "username": "testuser"}

    def tearDown(self):
        self.patch_uuid.stop()
        self.patch_logger_info.stop()
        super().tearDown()

    def test_handle_password_reset_request_user_found(self):
        self.mock_user_repo.find_by_email.return_value = self.mock_user
        
        self.password_reset_service.handle_password_reset_request(self.email)
        
        self.mock_user_repo.find_by_email.assert_called_once_with(
            self.db_conn, self.email
        )
        self.mock_uuid.assert_called_once()
        
        found_email_log = False
        for call_args in self.mock_logger_info.call_args_list:
            if "EMAIL SIMULASI" in call_args[0][0]:
                found_email_log = True
                self.assertIn(self.email, call_args[0][0])
                self.assertIn(
                    '12345678-1234-5678-1234-567812345678', call_args[0][0]
                )
                break
        self.assertTrue(found_email_log, "Simulated email log not found.")

    def test_handle_password_reset_request_user_not_found(self):
        self.mock_user_repo.find_by_email.return_value = None
        
        self.password_reset_service.handle_password_reset_request(self.email)
        
        self.mock_user_repo.find_by_email.assert_called_once_with(
            self.db_conn, self.email
        )
        self.mock_uuid.assert_not_called()

    def test_handle_password_reset_request_db_error(self):
        self.mock_user_repo.find_by_email.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.password_reset_service.handle_password_reset_request(self.email)

    def test_handle_password_reset_request_service_error(self):
        self.mock_user_repo.find_by_email.side_effect = (
            Exception("Service Error")
        )
        
        with self.assertRaises(ServiceLogicError):
            self.password_reset_service.handle_password_reset_request(self.email)