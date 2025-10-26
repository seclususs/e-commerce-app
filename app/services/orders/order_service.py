from typing import Any, Dict, Optional

from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.order_cancel_service import order_cancel_service
from app.services.orders.order_creation_service import order_creation_service
from app.services.orders.order_update_service import order_update_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class OrderService:

    def create_order(
        self,
        user_id: Optional[int],
        session_id: Optional[str],
        cart_data: Optional[Dict[str, Any]],
        shipping_details: Dict[str, Any],
        payment_method: str,
        voucher_code: Optional[str] = None,
        shipping_cost: float = 0,
    ) -> Dict[str, Any]:
        logger.debug("Mendelegasikan pembuatan pesanan ke OrderCreationService")

        try:
            return order_creation_service.create_order(
                user_id,
                session_id,
                cart_data,
                shipping_details,
                payment_method,
                voucher_code,
                shipping_cost,
            )
        
        except Exception as e:
            logger.error(
                f"Error caught in OrderService.create_order: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal memproses pembuatan pesanan: {e}")


    def cancel_user_order(self, order_id: int, user_id: int) -> Dict[str, Any]:
        logger.debug(
            "Mendelegasikan pembatalan pesanan pengguna ke OrderCancelService"
        )

        try:
            return order_cancel_service.cancel_user_order(order_id, user_id)
        
        except Exception as e:
            logger.error(
                f"Error caught in OrderService.cancel_user_order: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Gagal memproses pembatalan pesanan pengguna: {e}"
            )


    def update_order_status_and_tracking(
        self,
        order_id: int,
        new_status: str,
        tracking_number_input: Optional[str],
    ) -> Dict[str, Any]:
        logger.debug(
            "Mendelegasikan pembaruan status pesanan ke OrderUpdateService"
        )
        
        try:
            return order_update_service.update_order_status_and_tracking(
                order_id, new_status, tracking_number_input
            )
        
        except Exception as e:
            logger.error(
                f"Error caught in OrderService.update_order_status_and_tracking: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Gagal memproses pembaruan status pesanan: {e}"
            )

order_service = OrderService()