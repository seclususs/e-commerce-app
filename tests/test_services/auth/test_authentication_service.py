from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch

import mysql.connector

from app.services.auth.authentication_service import AuthenticationService
from app.exceptions.api_exceptions import AuthError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError


class TestAuthenticationService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_user_repo = MagicMock()

        self.patch_check_hash = patch(
            'app.services.auth.authentication_service.check_password_hash'
        )
        
        self.mock_check_hash = self.patch_check_hash.start()
        
        self.auth_service = AuthenticationService(
            user_repo=self.mock_user_repo
        )
        
        self.username = "testuser"
        self.password = "password123"
        self.mock_user = {
            "id": 1, "username": self.username, "password": "hashed_password"
        }

    def tearDown(self):
        self.patch_check_hash.stop()
        super().tearDown()

    def test_verify_user_login_success(self):
        self.mock_user_repo.find_by_username.return_value = self.mock_user
        self.mock_check_hash.return_value = True
        
        result = self.auth_service.verify_user_login(
            self.username, self.password
        )
        
        self.mock_user_repo.find_by_username.assert_called_once_with(
            self.db_conn, self.username
        )
        self.mock_check_hash.assert_called_once_with(
            "hashed_password", self.password
        )
        self.assertEqual(result, self.mock_user)

    def test_verify_user_login_user_not_found(self):
        self.mock_user_repo.find_by_username.return_value = None
        
        with self.assertRaises(AuthError) as cm:
            self.auth_service.verify_user_login(self.username, self.password)
            
        self.mock_check_hash.assert_not_called()
        self.assertIn("Username atau password salah", str(cm.exception))

    def test_verify_user_login_wrong_password(self):
        self.mock_user_repo.find_by_username.return_value = self.mock_user
        self.mock_check_hash.return_value = False
        
        with self.assertRaises(AuthError) as cm:
            self.auth_service.verify_user_login(self.username, self.password)
            
        self.mock_check_hash.assert_called_once()
        self.assertIn("Username atau password salah", str(cm.exception))

    def test_verify_user_login_db_error(self):
        self.mock_user_repo.find_by_username.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.auth_service.verify_user_login(self.username, self.password)

    def test_verify_user_login_service_error(self):
        self.mock_user_repo.find_by_username.side_effect = (
            Exception("Service Error")
        )
        
        with self.assertRaises(ServiceLogicError):
            self.auth_service.verify_user_login(self.username, self.password)