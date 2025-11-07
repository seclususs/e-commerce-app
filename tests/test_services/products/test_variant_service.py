from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

import mysql.connector

from app.services.products.variant_service import VariantService
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import RecordNotFoundError


class TestVariantService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_variant_repo = MagicMock()
        self.mock_product_repo = MagicMock()
        
        self.variant_service = VariantService(
            variant_repo=self.mock_variant_repo,
            product_repo=self.mock_product_repo
        )
        
        self.color = "DEFAULT_COLOR"

    def tearDown(self):
        super().tearDown()

    def test_get_variants_for_product_success(self):
        mock_variants = [{"id": 1, "size": "M"}]
        self.mock_variant_repo.find_by_product_id.return_value = mock_variants
        
        result = self.variant_service.get_variants_for_product(1)
        
        self.mock_variant_repo.find_by_product_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertEqual(result, mock_variants)

    def test_add_variant_success(self):
        self.mock_variant_repo.create.return_value = 1
        new_variant = {"id": 1, "size": "M", "color": self.color}
        self.mock_variant_repo.find_by_id.return_value = new_variant
        self.mock_variant_repo.get_total_stock.return_value = 10
        
        result = self.variant_service.add_variant(
            1, self.color, "M", 10, 100, None, None, "SKU1"
        )
        
        self.mock_variant_repo.create.assert_called_once_with(
            self.db_conn, 1, self.color, "M", 10, 100, None, None, "SKU1"
        )
        self.mock_variant_repo.get_total_stock.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_product_repo.update_stock.assert_called_once_with(
            self.db_conn, 1, 10
        )
        self.assertEqual(result["success"], True)
        self.assertEqual(result["data"], new_variant)

    def test_add_variant_validation_error_stock(self):
        with self.assertRaises(ValidationError):
            self.variant_service.add_variant(
                1, self.color, "M", -1, 100, None, None, "SKU1"
            )

    def test_add_variant_validation_error_type(self):
        with self.assertRaises(ValidationError):
            self.variant_service.add_variant(
                1, self.color, "M", "abc", 100, None, None, "SKU1"
            )

    def test_add_variant_integrity_error(self):
        self.mock_variant_repo.create.side_effect = (
            mysql.connector.IntegrityError(errno=1062, msg="sku")
        )
        
        result = self.variant_service.add_variant(
            1, self.color, "M", 10, 100, None, None, "SKU1"
        )

        self.assertEqual(result["success"], False)
        self.assertIn("SKU", result["message"])

    def test_update_variant_success(self):
        self.mock_variant_repo.update.return_value = 1
        self.mock_variant_repo.get_total_stock.return_value = 20
        
        result = self.variant_service.update_variant(
            1, 5, self.color, "L", 20, 150, None, None, "SKU2"
        )
        
        self.mock_variant_repo.update.assert_called_once_with(
            self.db_conn, 5, 1, self.color, "L", 20, 150, None, None, "SKU2"
        )
        self.mock_product_repo.update_stock.assert_called_once_with(
            self.db_conn, 1, 20
        )
        self.assertEqual(result["success"], True)

    def test_update_variant_not_found(self):
        self.mock_variant_repo.update.return_value = 0
        
        with self.assertRaises(RecordNotFoundError):
            self.variant_service.update_variant(
                1, 5, self.color, "L", 20, 150, None, None, "SKU2"
            )

    def test_delete_variant_success(self):
        self.mock_variant_repo.delete.return_value = 1
        self.mock_variant_repo.get_total_stock.return_value = 0
        
        result = self.variant_service.delete_variant(1, 5)
        
        self.mock_variant_repo.delete.assert_called_once_with(
            self.db_conn, 5, 1
        )
        self.mock_product_repo.update_stock.assert_called_once_with(
            self.db_conn, 1, 0
        )
        self.assertEqual(result["success"], True)