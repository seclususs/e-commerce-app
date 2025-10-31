from flask import url_for

from tests.base_test_case import BaseTestCase


class TestAuthLogoutRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_logout(self):
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            sess["is_admin"] = False
        
        with self.client.session_transaction() as sess:
            self.assertIn("user_id", sess)

        response = self.client.get(url_for("auth.logout"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(url_for("product.index", _external=False)))
        
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)
            self.assertNotIn("username", sess)