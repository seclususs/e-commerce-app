from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

import mysql.connector

from app.services.users.user_profile_service import UserProfileService
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError


class TestUserProfileService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_user_repo = MagicMock()
        
        self.user_profile_service = UserProfileService(
            user_repo=self.mock_user_repo
        )

    def tearDown(self):
        super().tearDown()

    def test_get_user_by_id_success(self):
        mock_user = {"id": 1, "username": "testuser"}
        self.mock_user_repo.find_by_id.return_value = mock_user
        
        user = self.user_profile_service.get_user_by_id(1)
        
        self.mock_user_repo.find_by_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertEqual(user, mock_user)

    def test_get_user_by_id_not_found(self):
        self.mock_user_repo.find_by_id.return_value = None
        
        with self.assertRaises(RecordNotFoundError):
            self.user_profile_service.get_user_by_id(1)

    def test_get_user_by_id_db_error(self):
        self.mock_user_repo.find_by_id.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.user_profile_service.get_user_by_id(1)

    def test_get_user_by_id_service_error(self):
        self.mock_user_repo.find_by_id.side_effect = Exception("Service Error")
        
        with self.assertRaises(ServiceLogicError):
            self.user_profile_service.get_user_by_id(1)

    def test_update_user_info_success(self):
        self.mock_user_repo.check_existing.return_value = None
        
        result = self.user_profile_service.update_user_info(
            1, "new_user", "new@mail.com"
        )
        
        self.mock_user_repo.check_existing.assert_called_once_with(
            self.db_conn, "new_user", "new@mail.com", 1
        )
        self.mock_user_repo.update_profile.assert_called_once_with(
            self.db_conn, 1, "new_user", "new@mail.com"
        )
        self.assertEqual(
            result,
            {"success": True, "message": "Informasi akun berhasil diperbarui."}
        )

    def test_update_user_info_conflict(self):
        self.mock_user_repo.check_existing.return_value = {"id": 2}
        
        with self.assertRaises(ValidationError):
            self.user_profile_service.update_user_info(
                1, "taken_user", "taken@mail.com"
            )
            
        self.mock_user_repo.update_profile.assert_not_called()

    def test_update_user_info_db_error(self):
        self.mock_user_repo.check_existing.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.user_profile_service.update_user_info(
                1, "new_user", "new@mail.com"
            )