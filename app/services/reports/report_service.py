from typing import Any, Dict, List, Optional

from app.exceptions.service_exceptions import ServiceLogicError

from .customer_report_service import customer_report_service
from .dashboard_report_service import (
    convert_decimals, dashboard_report_service
)
from .inventory_report_service import inventory_report_service
from .product_report_service import product_report_service
from .sales_report_service import sales_report_service


class ReportService:

    def get_dashboard_stats(
        self, start_date_str: str, end_date_str: str
    ) -> Dict[str, Any]:
        
        try:
            stats = dashboard_report_service.get_dashboard_stats(
                start_date_str, end_date_str
            )
            return convert_decimals(stats)
        
        except Exception as e:
            raise ServiceLogicError(f"Gagal mengambil statistik dasbor: {e}")


    def get_sales_summary(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, Any]:
        
        try:
            return sales_report_service.get_sales_summary(start_date, end_date)
        
        except Exception as e:
            raise ServiceLogicError(f"Gagal mengambil ringkasan penjualan: {e}")


    def get_voucher_effectiveness(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        
        try:
            return sales_report_service.get_voucher_effectiveness(
                start_date, end_date
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Gagal mengambil efektivitas voucher: {e}"
            )


    def get_full_sales_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        try:
            return sales_report_service.get_full_sales_data_for_export(
                start_date, end_date
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Gagal mengambil data penjualan untuk ekspor: {e}"
            )


    def get_full_vouchers_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        try:
            return sales_report_service.get_full_vouchers_data_for_export(
                start_date, end_date
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Gagal mengambil data voucher untuk ekspor: {e}"
            )


    def get_product_reports(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        
        try:
            return product_report_service.get_product_reports(
                start_date, end_date
            )
        
        except Exception as e:
            raise ServiceLogicError(f"Gagal mengambil laporan produk: {e}")


    def get_full_products_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        try:
            return product_report_service.get_full_products_data_for_export(
                start_date, end_date
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Gagal mengambil data produk untuk ekspor: {e}"
            )


    def get_customer_reports(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        
        try:
            return customer_report_service.get_customer_reports(
                start_date, end_date
            )
        
        except Exception as e:
            raise ServiceLogicError(f"Gagal mengambil laporan pelanggan: {e}")


    def get_cart_analytics(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, Any]:
        
        try:
            return customer_report_service.get_cart_analytics(
                start_date, end_date
            )
        
        except Exception as e:
            raise ServiceLogicError(f"Gagal mengambil analitik keranjang: {e}")


    def get_full_customers_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        try:
            return (
                customer_report_service.get_full_customers_data_for_export(
                    start_date, end_date
                )
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Gagal mengambil data pelanggan untuk ekspor: {e}"
            )


    def get_inventory_reports(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, Any]:
        
        try:
            return inventory_report_service.get_inventory_reports(
                start_date, end_date
            )
        
        except Exception as e:
            raise ServiceLogicError(f"Gagal mengambil laporan inventaris: {e}")


    def get_inventory_low_stock_for_export(self) -> List[List[Any]]:

        try:
            return (
                inventory_report_service.get_inventory_low_stock_for_export()
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Gagal mengambil data stok rendah untuk ekspor: {e}"
            )


    def get_inventory_slow_moving_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        try:
            return (
                inventory_report_service
                .get_inventory_slow_moving_for_export(
                    start_date, end_date
                )
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Gagal mengambil data produk lambat terjual untuk ekspor: "
                f"{e}"
            )

report_service = ReportService()