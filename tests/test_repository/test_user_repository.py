from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.user_repository import UserRepository, user_repository


class TestUserRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        self.cursor_patch = patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        )
        self.cursor_patch.start()
        self.repository = UserRepository()

    def tearDown(self):
        self.cursor_patch.stop()
        super().tearDown()

    def test_singleton_instance(self):
        self.assertIsInstance(user_repository, UserRepository)

    def test_find_by_id(self):
        mock_result = {"id": 1, "username": "test"}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_by_id(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM users WHERE id = %s", (1,)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_username(self):
        mock_result = {"id": 1, "username": "test"}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_by_username(self.db_conn, "test")

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM users WHERE username = %s", ("test",)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_email(self):
        mock_result = {"id": 1, "email": "a@b.c"}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_by_email(self.db_conn, "a@b.c")

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM users WHERE email = %s", ("a@b.c",)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_check_existing(self):
        self.repository.check_existing(self.db_conn, "test", "a@b.c", 1)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT id FROM users WHERE (username = %s OR email = %s) "
            "AND id != %s",
            ("test", "a@b.c", 1)
        )
        self.mock_cursor.close.assert_called_once()

    def test_create(self):
        self.mock_cursor.lastrowid = 2
        
        result = self.repository.create(
            self.db_conn, "new", "new@b.c", "hash", full_name="new"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "INSERT INTO users (username, email, password, full_name) "
            "VALUES (%s, %s, %s, %s)",
            ("new", "new@b.c", "hash", "new")
        )
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()

    def test_create_guest(self):
        details = {
            "username": "guest1", "email": "g@b.c", "phone": "123",
            "address1": "Jalan 1", "city": "Kota", "province": "Prov",
            "postal_code": "12345",
            "name": "Guest One"
        }
        self.mock_cursor.lastrowid = 3
        
        result = self.repository.create_guest(self.db_conn, details, "hash2")

        self.mock_cursor.execute.assert_called_once()
        params = self.mock_cursor.execute.call_args[0][1]
        
        self.assertEqual(params, (
            "guest1", "g@b.c", "hash2", "123", "Jalan 1", "",
            "Kota", "Prov", "12345", "Guest One"
        ))
        self.assertEqual(result, 3)
        self.mock_cursor.close.assert_called_once()

    def test_update_profile(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.update_profile(
            self.db_conn, 1, "updated", "u@b.c"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE users SET username = %s, email = %s WHERE id = %s",
            ("updated", "u@b.c", 1)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_update_password(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.update_password(
            self.db_conn, 1, "new_hash"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE users SET password = %s WHERE id = %s",
            ("new_hash", 1)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_update_address(self):
        address_data = {
            "full_name": "User 456",
            "phone": "456", "address1": "Jalan 2", "address2": "Apt 1",
            "city": "Kota 2", "province": "Prov 2", "postal_code": "54321"
        }
        self.mock_cursor.rowcount = 1
        
        result = self.repository.update_address(self.db_conn, 1, address_data)

        self.mock_cursor.execute.assert_called_once()
        params = self.mock_cursor.execute.call_args[0][1]
        
        self.assertEqual(params, (
            "User 456", "456", "Jalan 2", "Apt 1", "Kota 2", "Prov 2", "54321", 1
        ))
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()