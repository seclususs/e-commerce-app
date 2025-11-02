from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch

from app.services.auth.registration_service import RegistrationService
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.service_exceptions import ServiceLogicError


class TestRegistrationService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_validation_svc = MagicMock()
        self.mock_user_repo = MagicMock()
        self.mock_voucher_svc = MagicMock()
        
        self.patch_gen_hash = patch(
            'app.services.auth.registration_service.generate_password_hash',
            return_value="hashed_password"
        )
        self.patch_random = patch(
            'app.services.auth.registration_service.random.randint',
            return_value=123
        )
        
        self.mock_gen_hash = self.patch_gen_hash.start()
        self.mock_random = self.patch_random.start()
        
        self.registration_service = RegistrationService(
            validation_svc=self.mock_validation_svc,
            user_repo=self.mock_user_repo,
            voucher_svc=self.mock_voucher_svc
        )
        
        self.username = "newuser"
        self.email = "new@example.com"
        self.password = "password123"
        self.mock_new_user = {"id": 1, "username": self.username, "is_admin": False}
        self.guest_details = {
            "name": "Guest User", "email": "guest@mail.com", "phone": "123"
        }

    def tearDown(self):
        self.patch_gen_hash.stop()
        self.patch_random.stop()
        super().tearDown()

    def test_register_new_user_success(self):
        self.mock_validation_svc.validate_username_availability.return_value = (
            True, ""
        )
        self.mock_validation_svc.validate_email_availability.return_value = (
            True, ""
        )
        self.mock_user_repo.create.return_value = 1
        self.mock_user_repo.find_by_id.return_value = self.mock_new_user
        
        result = self.registration_service.register_new_user(
            self.username, self.email, self.password
        )
        
        self.mock_gen_hash.assert_called_once_with(self.password)
        self.mock_user_repo.create.assert_called_once_with(
            self.db_conn, self.username, self.email, "hashed_password"
        )
        self.mock_voucher_svc.grant_welcome_voucher.assert_called_once_with(
            self.db_conn, 1
        )
        self.db_conn.commit.assert_called_once()
        self.assertEqual(result, self.mock_new_user)

    def test_register_new_user_username_taken(self):
        self.mock_validation_svc.validate_username_availability.return_value = (
            False, ""
        )
        
        with self.assertRaises(ValidationError) as cm:
            self.registration_service.register_new_user(
                self.username, self.email, self.password
            )
            
        self.mock_validation_svc.validate_email_availability.assert_not_called()
        self.mock_user_repo.create.assert_not_called()
        self.mock_voucher_svc.grant_welcome_voucher.assert_not_called()
        self.assertIn("Username", str(cm.exception))

    def test_register_new_user_email_taken(self):
        self.mock_validation_svc.validate_username_availability.return_value = (
            True, ""
        )
        self.mock_validation_svc.validate_email_availability.return_value = (
            False, ""
        )
        
        with self.assertRaises(ValidationError) as cm:
            self.registration_service.register_new_user(
                self.username, self.email, self.password
            )
            
        self.mock_user_repo.create.assert_not_called()
        self.mock_voucher_svc.grant_welcome_voucher.assert_not_called()
        self.assertIn("Email", str(cm.exception))

    def test_register_guest_user_success(self):
        self.mock_validation_svc.validate_email_availability.return_value = (
            True, ""
        )
        self.mock_validation_svc.validate_username_availability.return_value = (
            True, ""
        )
        self.mock_user_repo.create_guest.return_value = 2
        mock_guest_user = {"id": 2, "username": "guestuser", "is_admin": False}
        self.mock_user_repo.find_by_id.return_value = mock_guest_user
        
        result = self.registration_service.register_guest_user(
            self.guest_details, self.password
        )
        
        self.mock_gen_hash.assert_called_once_with(self.password)
        expected_details = {**self.guest_details, "username": "guestuser"}
        self.mock_user_repo.create_guest.assert_called_once_with(
            self.db_conn, expected_details, "hashed_password"
        )
        self.mock_voucher_svc.grant_welcome_voucher.assert_called_once_with(
            self.db_conn, 2
        )
        self.db_conn.commit.assert_called_once()
        self.assertEqual(result, mock_guest_user)

    def test_register_guest_user_email_taken(self):
        self.mock_validation_svc.validate_email_availability.return_value = (
            False, ""
        )
        
        with self.assertRaises(ValidationError) as cm:
            self.registration_service.register_guest_user(
                self.guest_details, self.password
            )
            
        self.mock_validation_svc.validate_username_availability.assert_not_called()
        self.mock_voucher_svc.grant_welcome_voucher.assert_not_called()
        self.assertIn("Email sudah terdaftar", str(cm.exception))

    def test_register_guest_user_cannot_generate_username(self):
        self.mock_validation_svc.validate_email_availability.return_value = (
            True, ""
        )
        self.mock_validation_svc.validate_username_availability.return_value = (
            False, ""
        )
        
        with self.assertRaises(ServiceLogicError) as cm:
            self.registration_service.register_guest_user(
                self.guest_details, self.password
            )
            
        self.assertEqual(
            self.mock_validation_svc.validate_username_availability.call_count,
            10
        )
        self.mock_voucher_svc.grant_welcome_voucher.assert_not_called()
        self.assertIn("Gagal membuat username unik", str(cm.exception))