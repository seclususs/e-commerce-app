from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch

import mysql.connector

from app.services.users.user_service import UserService
from app.exceptions.api_exceptions import AuthError, ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)


class TestUserService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_user_repo = MagicMock()
        
        self.patch_check_hash = patch(
            'app.services.users.user_service.check_password_hash',
            return_value=True
        )
        self.patch_gen_hash = patch(
            'app.services.users.user_service.generate_password_hash',
            return_value="new_hashed_password"
        )
        
        self.mock_check_hash = self.patch_check_hash.start()
        self.mock_gen_hash = self.patch_gen_hash.start()
        
        self.user_service = UserService(user_repo=self.mock_user_repo)

    def tearDown(self):
        self.patch_check_hash.stop()
        self.patch_gen_hash.stop()
        super().tearDown()

    def test_get_user_by_id_success(self):
        mock_user = {"id": 1, "username": "testuser"}
        self.mock_user_repo.find_by_id.return_value = mock_user
        
        user = self.user_service.get_user_by_id(1)
        
        self.mock_user_repo.find_by_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertEqual(user, mock_user)

    def test_get_user_by_id_not_found(self):
        self.mock_user_repo.find_by_id.return_value = None
        
        with self.assertRaises(RecordNotFoundError):
            self.user_service.get_user_by_id(1)

    def test_update_user_info_success(self):
        self.mock_user_repo.check_existing.return_value = None
        
        result = self.user_service.update_user_info(
            1, "new_user", "new@mail.com"
        )
        
        self.assertEqual(
            result,
            {"success": True, "message": "Informasi akun berhasil diperbarui."}
        )

    def test_update_user_info_conflict(self):
        self.mock_user_repo.check_existing.return_value = {"id": 2}
        
        with self.assertRaises(ValidationError):
            self.user_service.update_user_info(
                1, "taken_user", "taken@mail.com"
            )

    def test_change_user_password_success(self):
        mock_user = {"id": 1, "password": "hashed_password"}
        self.mock_user_repo.find_by_id.return_value = mock_user
        self.mock_check_hash.return_value = True
        
        result = self.user_service.change_user_password(
            1, "current_pass", "new_pass"
        )
        
        self.mock_user_repo.find_by_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_check_hash.assert_called_once_with(
            "hashed_password", "current_pass"
        )
        self.mock_gen_hash.assert_called_once_with("new_pass")
        self.mock_user_repo.update_password.assert_called_once_with(
            self.db_conn, 1, "new_hashed_password"
        )
        self.assertEqual(
            result,
            {"success": True, "message": "Password berhasil diubah."}
        )

    def test_change_user_password_wrong_password(self):
        mock_user = {"id": 1, "password": "hashed_password"}
        self.mock_user_repo.find_by_id.return_value = mock_user
        self.mock_check_hash.return_value = False
        
        with self.assertRaises(AuthError):
            self.user_service.change_user_password(
                1, "wrong_pass", "new_pass"
            )

    def test_change_user_password_user_not_found(self):
        self.mock_user_repo.find_by_id.return_value = None

        with self.assertRaises(AuthError):
            self.user_service.change_user_password(
                1, "any_pass", "new_pass"
            )

    def test_update_user_address_success(self):
        address_data = {"phone": "123", "address1": "Street 1"}
        
        result = self.user_service.update_user_address(1, address_data)
        
        self.mock_user_repo.update_address.assert_called_once_with(
            self.db_conn, 1, address_data
        )
        self.assertEqual(
            result,
            {"success": True, "message": "Alamat berhasil diperbarui."}
        )

    def test_update_user_address_external_conn(self):
        address_data = {"phone": "123", "address1": "Street 1"}
        external_conn = MagicMock()
        
        result = self.user_service.update_user_address(
            1, address_data, external_conn
        )
        
        self.mock_user_repo.update_address.assert_called_once_with(
            external_conn, 1, address_data
        )
        self.assertEqual(
            result,
            {"success": True, "message": "Alamat berhasil diperbarui."}
        )

    def test_update_user_address_db_error(self):
        address_data = {"phone": "123", "address1": "Street 1"}
        self.mock_user_repo.update_address.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.user_service.update_user_address(1, address_data)