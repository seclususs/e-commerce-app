from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch

from app.services.products.product_query_service import ProductQueryService


class TestProductQueryService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_product_repo = MagicMock()
        self.mock_variant_repo = MagicMock()
        self.mock_stock_svc = MagicMock()
        self.mock_variant_svc = MagicMock()
        
        self.patch_json_loads = patch(
            'app.services.products.product_query_service.json.loads'
        )
        
        self.mock_json_loads = self.patch_json_loads.start()
        
        self.product_query_service = ProductQueryService(
            product_repo=self.mock_product_repo,
            variant_repo=self.mock_variant_repo,
            stock_svc=self.mock_stock_svc,
            variant_svc=self.mock_variant_svc
        )

    def tearDown(self):
        self.patch_json_loads.stop()
        super().tearDown()

    def test_get_filtered_products_success(self):
        mock_products = [{"id": 1, "name": "Product"}]
        self.mock_product_repo.find_filtered.return_value = mock_products
        filters = {"search": "Product"}
        
        result = self.product_query_service.get_filtered_products(filters)
        
        self.mock_product_repo.find_filtered.assert_called_once_with(
            self.db_conn, filters
        )
        self.assertEqual(result, mock_products)

    def test_get_all_products_with_category_success(self):
        mock_products = [{"id": 1, "name": "Product"}]
        self.mock_product_repo.find_all_with_category.return_value = (
            mock_products
        )
        
        result = self.product_query_service.get_all_products_with_category(
            search="Prod", category_id=1, stock_status="in_stock"
        )
        
        (
            self.mock_product_repo.
            find_all_with_category.assert_called_once_with(
                self.db_conn, "Prod", 1, "in_stock"
            )
        )
        self.assertEqual(result, mock_products)

    def test_get_product_by_id_success_no_variants(self):
        mock_product = {
            "id": 1, "name": "Test", "has_variants": False,
            "image_url": "main.jpg", "additional_image_urls": '["add.jpg"]'
        }
        self.mock_product_repo.find_with_category.return_value = mock_product
        self.mock_json_loads.return_value = ["add.jpg"]
        self.mock_variant_svc.get_variants_for_product.return_value = []
        self.mock_stock_svc.get_available_stock.return_value = 10
        
        result = self.product_query_service.get_product_by_id(1)
        
        self.mock_product_repo.update_popularity.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_json_loads.assert_called_once_with('["add.jpg"]')
        self.mock_stock_svc.get_available_stock.assert_called_once_with(
            1, None, self.db_conn
        )
        self.assertEqual(result["stock"], 10)
        self.assertEqual(result["all_images"], ["main.jpg", "add.jpg"])

    def test_get_product_by_id_success_with_variants(self):
        mock_product = {
            "id": 1, "name": "Test", "has_variants": True,
            "image_url": "main.jpg", "additional_image_urls": None,
            "price": 10000, "discount_price": None
        }
        mock_variants = [
            {"id": 10, "size": "M", "color": "RED"}, 
            {"id": 11, "size": "L", "color": "BLUE"}
        ]
        self.mock_product_repo.find_with_category.return_value = mock_product
        
        self.mock_variant_svc.get_variants_for_product.return_value = (
            mock_variants
        )
        self.mock_stock_svc.get_available_stock.side_effect = [5, 8]
        
        result = self.product_query_service.get_product_by_id(1)
        
        self.assertEqual(
            self.mock_stock_svc.get_available_stock.call_count, 2
        )
        self.assertEqual(result["variants"][0]["stock"], 5)
        self.assertEqual(result["variants"][1]["stock"], 8)
        self.assertEqual(result["variants"][0]["price"], 10000)
        self.assertNotIn("stock", result)
        self.assertEqual(result["unique_colors"], ["BLUE", "RED"])
        self.assertEqual(result["unique_sizes"], ["L", "M"])

    def test_get_product_by_id_not_found(self):
        self.mock_product_repo.find_with_category.return_value = None
        
        result = self.product_query_service.get_product_by_id(1)
        
        self.assertIsNone(result)

    def test_get_related_products_success(self):
        mock_products = [{"id": 2, "name": "Related"}]
        self.mock_product_repo.find_related.return_value = mock_products
        
        result = self.product_query_service.get_related_products(1, 5)
        
        self.mock_product_repo.find_related.assert_called_once_with(
            self.db_conn, 1, 5
        )
        self.assertEqual(result, mock_products)