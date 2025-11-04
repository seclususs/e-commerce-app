import json
from unittest.mock import patch
from decimal import Decimal

from flask import url_for

from app.exceptions.api_exceptions import ValidationError
from tests.base_test_case import BaseTestCase


class TestAdminMembershipRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin_patch = patch(
            "app.utils.route_decorators.session",
            {"user_id": 1, "is_admin": True, "username": "admin"},
        )
        self.mock_session = self.login_admin_patch.start()

        self.membership_service_patch = patch(
            "app.routes.admin.membership_routes.membership_service"
        )
        self.mock_membership_service = self.membership_service_patch.start()
        
        self.get_content_patch = patch("app.routes.admin.membership_routes.get_content")
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {}

        self.mock_plan = {
            "id": 1, "name": "Gold", "price": Decimal("100000"),
            "period": "monthly", "is_active": True,
            "discount_percent": Decimal("10.0")
        }
        self.form_data = {
            "action": "add", "name": "Gold", "price": "100000",
            "period": "monthly", "discount_percent": "10",
            "free_shipping": "on", "is_active": "on",
            "description": "Test"
        }

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_memberships_get_success(self):
        self.mock_membership_service.get_all_memberships_for_admin.return_value = [
            self.mock_plan
        ]
        response = self.client.get(url_for("admin.admin_memberships"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Manajemen Paket Membership", response.data)
        self.assertIn(b"Gold", response.data)

    def test_admin_memberships_get_ajax_success(self):
        self.mock_membership_service.get_all_memberships_for_admin.return_value = [
            self.mock_plan
        ]
        response = self.client.get(
            url_for("admin.admin_memberships"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)
        self.assertIn("Gold", data["html"])

    def test_admin_memberships_post_add_success(self):
        self.mock_membership_service.create_membership.return_value = {
            "success": True, "data": self.mock_plan
        }
        response = self.client.post(
            url_for("admin.admin_memberships"), data=self.form_data
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)
        self.mock_membership_service.create_membership.assert_called_once()

    def test_admin_memberships_post_add_validation_error(self):
        self.mock_membership_service.create_membership.side_effect = ValidationError(
            "Harga tidak valid"
        )
        response = self.client.post(
            url_for("admin.admin_memberships"), data=self.form_data
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Harga tidak valid", data["message"])

    def test_admin_memberships_post_update_success(self):
        update_data = self.form_data.copy()
        update_data["action"] = "update"
        update_data["membership_id"] = "1"
        self.mock_membership_service.update_membership.return_value = {
            "success": True, "data": self.mock_plan
        }
        
        response = self.client.post(
            url_for("admin.admin_memberships"), data=update_data
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.mock_membership_service.update_membership.assert_called_once()

    def test_delete_membership_post_success(self):
        self.mock_membership_service.delete_membership.return_value = {
            "success": True
        }
        response = self.client.post(
            url_for("admin.delete_membership", id=1)
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_delete_membership_post_fail(self):
        self.mock_membership_service.delete_membership.return_value = {
            "success": False, "message": "Gagal"
        }
        response = self.client.post(
            url_for("admin.delete_membership", id=1)
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])