from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch

import mysql.connector

from app.services.products.product_service import ProductService


class TestProductService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_product_repo = MagicMock()
        self.mock_variant_repo = MagicMock()
        self.mock_image_svc = MagicMock()
        self.mock_variant_conv_svc = MagicMock()
        self.mock_variant_svc = MagicMock()
        self.mock_stock_svc = MagicMock()
        
        self.patch_get_db_extra = patch(
            'app.services.products.product_service.get_db_connection',
            return_value=self.db_conn 
        )
        self.patch_get_db_extra.start()
        
        self.product_service = ProductService(
            product_repo=self.mock_product_repo,
            variant_repo=self.mock_variant_repo,
            image_svc=self.mock_image_svc,
            variant_conversion_svc=self.mock_variant_conv_svc,
            variant_svc=self.mock_variant_svc,
            stock_svc=self.mock_stock_svc
        )
        
        self.mock_form = {
            "name": "Test Product", "price": 100, "category_id": 1,
            "description": "Desc", "stock": 10, "weight_grams": 100
        }
        self.mock_files = {}

    def tearDown(self):
        self.patch_get_db_extra.stop()
        super().tearDown()

    def test_create_product_success(self):
        self.mock_image_svc.handle_image_upload.return_value = (
            "main.jpg", ["add.jpg"], [], [], None
        )
        self.mock_product_repo.create.return_value = 1
        
        new_product = {
            "id": 1, 
            "name": "Test Product",
            "additional_image_urls": '["add.jpg"]',
            "image_url": "main.jpg"
        }
        self.mock_product_repo.find_with_category.return_value = new_product
        self.mock_stock_svc.get_available_stock.return_value = 10
        
        result = self.product_service.create_product(
            self.mock_form, self.mock_files
        )
        
        self.mock_image_svc.handle_image_upload.assert_called_once()
        self.mock_product_repo.create.assert_called_once()
        self.mock_stock_svc.get_available_stock.assert_called_once_with(1, None, self.db_conn)
        self.assertEqual(result["success"], True)
        self.assertIn("all_images", result["product"])
        self.assertEqual(result["product"]["all_images"], ["main.jpg", "add.jpg"])
        self.assertEqual(result["product"]["stock"], 10)

    def test_create_product_image_error(self):
        self.mock_image_svc.handle_image_upload.return_value = (
            None, [], [], [], "Image error"
        )
        
        result = self.product_service.create_product(
            self.mock_form, self.mock_files
        )
        
        self.assertEqual(result, {"success": False, "message": "Image error"})
        
    def test_create_product_validation_error(self):
        invalid_form = self.mock_form.copy()
        del invalid_form["name"]

        self.mock_image_svc.handle_image_upload.return_value = (
            "main.jpg", ["add.jpg"], [], [], None
        )
        
        result = self.product_service.create_product(
            invalid_form, self.mock_files
        )
        self.assertEqual(result["success"], False)
        self.assertIn("wajib diisi", result["message"])


    def test_create_product_integrity_error_sku(self):
        self.mock_image_svc.handle_image_upload.return_value = (
            "main.jpg", [], [], [], None
        )
        self.mock_product_repo.create.side_effect = (
            mysql.connector.IntegrityError(errno=1062, msg="sku")
        )
        form_with_sku = self.mock_form.copy()
        form_with_sku["sku"] = "DUP-123"
        
        result = self.product_service.create_product(
            form_with_sku, self.mock_files
        )
        
        self.assertEqual(result["success"], False)
        self.assertIn("SKU", result["message"])

    def test_update_product_success(self):
        mock_product = {"id": 1, "has_variants": False}
        self.mock_product_repo.find_by_id.return_value = mock_product
        self.mock_image_svc.handle_image_upload.return_value = (
            "main.jpg", [], [], [], None
        )
        self.mock_product_repo.update.return_value = 1
        
        result = self.product_service.update_product(
            1, self.mock_form, self.mock_files
        )
        
        self.mock_product_repo.find_by_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_product_repo.update.assert_called_once()
        self.assertEqual(result["success"], True)

    def test_update_product_to_variant(self):
        mock_product = {"id": 1, "has_variants": False, "stock": 10}
        self.mock_product_repo.find_by_id.return_value = mock_product
        self.mock_image_svc.handle_image_upload.return_value = (
            "main.jpg", [], [], [], None
        )
        self.mock_variant_conv_svc.convert_to_variant_product.return_value = (
            10, 0, None
        )
        self.mock_product_repo.update.return_value = 1
        
        form_with_variant = self.mock_form.copy()
        form_with_variant["has_variants"] = "on"
        
        result = self.product_service.update_product(
            1, form_with_variant, self.mock_files
        )
        
        (
            self.mock_variant_conv_svc.
            convert_to_variant_product.assert_called_once_with(
                1, mock_product, self.db_conn
            )
        )
        self.assertEqual(result["success"], True)
        self.mock_variant_svc.update_total_stock_from_variants.assert_called()

    def test_delete_product_success(self):
        mock_product = {"id": 1, "image_url": "main.jpg"}
        
        self.mock_product_repo.find_by_id.return_value = mock_product
        self.mock_product_repo.delete.return_value = 1
        result = self.product_service.delete_product(1)
            
        self.mock_product_repo.find_by_id.assert_called_once_with(
            self.db_conn, 1
            )
        self.mock_variant_svc.delete_all_variants_for_product.assert_called_once_with(
            1, self.db_conn
            )
        self.mock_product_repo.delete.assert_called_once_with(
            self.db_conn, 1
            )
        self.mock_image_svc.delete_all_product_images.assert_called_once_with(
                mock_product
            )
        self.assertEqual(result["success"], True)