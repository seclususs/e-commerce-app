from unittest.mock import MagicMock, patch

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestCommonImageRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.app.config["IMAGE_FOLDER"] = "/test/image/folder"
        self.send_from_dir_patch = patch(
            "app.routes.common.image_routes.send_from_directory"
        )
        self.mock_send_from_dir = self.send_from_dir_patch.start()

        self.isfile_patch = patch("app.routes.common.image_routes.os.path.isfile")
        self.mock_isfile = self.isfile_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_serve_image_success(self):
        self.mock_isfile.return_value = True
        self.mock_send_from_dir.return_value = MagicMock(status_code=200)
        response = self.client.get(url_for("images.serve_image", filename="test.jpg"))
        self.assertEqual(response.status_code, 200)
        self.mock_send_from_dir.assert_called_once_with(
            "/test/image/folder", "test.jpg"
        )

    def test_serve_image_not_found(self):
        self.mock_isfile.return_value = False
        response = self.client.get(
            url_for("images.serve_image", filename="notfound.jpg")
        )
        self.assertEqual(response.status_code, 404)
        self.mock_send_from_dir.assert_not_called()

    def test_serve_image_path_traversal(self):
        response = self.client.get(
            url_for("images.serve_image", filename="../secret.txt")
        )
        self.assertEqual(response.status_code, 400)
        self.mock_send_from_dir.assert_not_called()

    def test_serve_image_no_config(self):
        del self.app.config["IMAGE_FOLDER"]
        response = self.client.get(
            url_for("images.serve_image", filename="test.jpg")
        )
        self.assertEqual(response.status_code, 404)