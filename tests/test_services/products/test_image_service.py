from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch

from app.services.products.image_service import ImageService


class TestImageService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.image_service = ImageService()

        self.mock_current_app = patch(
            'app.services.products.image_service.current_app'
        ).start()
        self.mock_current_app.config = {'IMAGE_FOLDER': '/fake/path'}

        self.mock_save_image = patch(
            'app.services.products.image_service.save_compressed_image'
        ).start()

        self.mock_json_loads = patch(
            'app.services.products.image_service.json.loads'
        ).start()
        self.mock_os_path_join = patch(
            'app.services.products.image_service.os.path.join'
        ).start()
        self.mock_os_path_isfile = patch(
            'app.services.products.image_service.os.path.isfile'
        ).start()
        self.mock_os_remove = patch(
            'app.services.products.image_service.os.remove'
        ).start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_handle_image_upload_new_product(self):
        mock_file = MagicMock()
        mock_file.filename = "new_image.jpg"
        mock_files = MagicMock()
        mock_files.getlist.return_value = [mock_file]
        
        mock_form_data = MagicMock()
        mock_form_data.get.return_value = "new_image.jpg"
        
        self.mock_save_image.return_value = "saved_new.jpg"
        
        (main, additional, deleted, marked, err) = (
            self.image_service.handle_image_upload(mock_files, mock_form_data)
        )
        
        self.mock_save_image.assert_called_once_with(mock_file)
        self.assertEqual(main, "saved_new.jpg")
        self.assertEqual(additional, [])
        self.assertEqual(deleted, [])
        self.assertIsNone(err)

    def test_handle_image_upload_update_delete_one(self):
        mock_files = MagicMock()
        mock_files.getlist.return_value = []
        
        mock_form_data = MagicMock()
        mock_form_data.getlist.return_value = ["existing_2.jpg"]
        mock_form_data.get.return_value = "existing_1.jpg"
        
        existing_product = {
            "image_url": "existing_1.jpg",
            "additional_image_urls": '["existing_2.jpg", "existing_3.jpg"]'
        }
        
        self.mock_json_loads.return_value = [
            "existing_2.jpg", "existing_3.jpg"
        ]
        self.mock_os_path_isfile.return_value = True
        
        (main, additional, deleted, marked, err) = (
            self.image_service.handle_image_upload(
                mock_files, mock_form_data, existing_product
            )
        )
        
        self.mock_save_image.assert_not_called()
        self.assertEqual(main, "existing_1.jpg")
        self.assertEqual(additional, ["existing_3.jpg"])
        self.assertEqual(deleted, ["existing_2.jpg"])
        self.assertIsNone(err)

    def test_handle_image_upload_no_images_error(self):
        mock_files = MagicMock()
        mock_files.getlist.return_value = []
        mock_form_data = MagicMock()
        mock_form_data.getlist.return_value = ["existing_1.jpg"]
        
        existing_product = {"image_url": "existing_1.jpg"}
        self.mock_os_path_isfile.return_value = True
        
        (main, additional, deleted, marked, err) = (
            self.image_service.handle_image_upload(
                mock_files, mock_form_data, existing_product
            )
        )
        
        self.assertIsNone(main)
        self.assertEqual(additional, [])
        self.assertEqual(deleted, ["existing_1.jpg"])
        self.assertIsNotNone(err)

    def test_delete_all_product_images(self):
        product = {
            "id": 1,
            "image_url": "main.jpg",
            "additional_image_urls": '["add_1.jpg", "add_2.jpg"]'
        }
        self.mock_json_loads.return_value = ["add_1.jpg", "add_2.jpg"]
        self.mock_os_path_isfile.return_value = True
        
        deleted_files = self.image_service.delete_all_product_images(product)
        
        self.assertEqual(len(deleted_files), 3)
        self.assertIn("main.jpg", deleted_files)
        self.assertIn("add_1.jpg", deleted_files)
        self.mock_os_remove.assert_called()