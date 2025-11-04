from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

import mysql.connector

from app.services.products.variant_conversion_service import (
    VariantConversionService
)
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError


class TestVariantConversionService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_product_repo = MagicMock()
        self.mock_variant_svc = MagicMock()
        
        self.variant_conversion_service = VariantConversionService(
            product_repo=self.mock_product_repo,
            variant_svc=self.mock_variant_svc
        )
        
        self.product_data = {
            "id": 1, "stock": 10, "weight_grams": 100, "sku": "P123"
        }

    def tearDown(self):
        super().tearDown()

    def test_convert_to_variant_product_success(self):
        self.mock_variant_svc.add_variant.return_value = {"success": True}
        
        result = (
            self.variant_conversion_service.convert_to_variant_product(
                1, self.product_data, self.db_conn
            )
        )
        
        self.mock_variant_svc.add_variant.assert_called_once_with(
            1, "STANDAR", "STANDAR", 10, 100, "P123"
        )
        (
            self.mock_product_repo.
            update_stock_sku_weight_variant_status.
            assert_called_once_with(
                self.db_conn, 1, 10, 0, None, True
            )
        )
        self.assertEqual(result, (10, 0, None))

    def test_convert_to_variant_product_add_fail(self):
        self.mock_variant_svc.add_variant.return_value = {
            "success": False, "message": "Failed"
        }
        
        with self.assertRaises(ServiceLogicError):
            (
                self.variant_conversion_service.
                convert_to_variant_product(
                    1, self.product_data, self.db_conn
                )
            )
            
        (
            self.mock_product_repo.
            update_stock_sku_weight_variant_status.
            assert_not_called()
        )

    def test_convert_to_variant_product_db_error(self):
        self.mock_variant_svc.add_variant.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            (
                self.variant_conversion_service.
                convert_to_variant_product(
                    1, self.product_data, self.db_conn
                )
            )

    def test_convert_from_variant_product_success(self):
        mock_form_data = {
            "stock": 20, "weight_grams": 200, "sku": "NEW-SKU"
        }
        
        result = (
            self.variant_conversion_service.convert_from_variant_product(
                1, mock_form_data, self.db_conn
            )
        )
        
        (
            self.mock_variant_svc.
            delete_all_variants_for_product.
            assert_called_once_with(
                1, self.db_conn
            )
        )
        (
            self.mock_product_repo.
            update_stock_sku_weight_variant_status.
            assert_called_once_with(
                self.db_conn, 1, 20, 200, "NEW-SKU", False
            )
        )
        self.assertEqual(result, (20, 200, "NEW-SKU"))

    def test_convert_from_variant_product_db_error(self):
        (
            self.mock_variant_svc.
            delete_all_variants_for_product.side_effect
        ) = mysql.connector.Error("DB Error")
        
        with self.assertRaises(DatabaseException):
            (
                self.variant_conversion_service.
                convert_from_variant_product(
                    1, {}, self.db_conn
                )
            )