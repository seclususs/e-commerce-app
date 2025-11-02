import json
from typing import Any, Dict, List, Optional

import mysql.connector
from flask import session, url_for

from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.services.orders.checkout_validation_service import (
    checkout_validation_service
)
from app.services.orders.order_creation_service import (
    order_creation_service
)
from app.services.orders.stock_service import stock_service
from app.services.users.user_service import user_service
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class CheckoutService:

    def process_checkout(
        self,
        user_id: Optional[int],
        session_id: Optional[str],
        form_data: Dict[str, Any],
        guest_cart_json: Optional[str],
    ) -> Dict[str, Any]:
        user: Optional[Dict[str, Any]] = (
            user_service.get_user_by_id(user_id) if user_id else None
        )
        user_log_id: str = (
            f"User {user_id}" if user_id else f"Session {session_id}"
        )
        cart_data: Optional[Dict[str, Any]] = None
        shipping_details: Dict[str, Any] = {}

        try:
            if user_id:

                if not user:
                    logger.error(
                        f"ID Pengguna {user_id} tidak ditemukan "
                        f"selama checkout."
                    )
                    session.clear()
                    return {
                        "success": False,
                        "redirect": url_for("auth.login"),
                        "message": "Terjadi kesalahan, pengguna tidak ditemukan.",
                        "flash_category": "danger",
                    }

                pending_order: Optional[Dict[str, Any]] = (
                    checkout_validation_service.check_pending_order(user_id)
                )

                if pending_order:
                    held_items: List[Dict[str, Any]] = (
                        stock_service.get_held_items_simple(
                            user_id=user_id, session_id=None
                        )
                    )

                    if not held_items:
                        logger.warning(
                            f"Checkout pengguna {user_id}: Penahanan stok "
                            f"kedaluwarsa saat memiliki pesanan tertunda "
                            f"{pending_order['id']}."
                        )
                        return {
                            "success": False,
                            "redirect": url_for("purchase.cart_page"),
                            "message": ("Sesi checkout Anda berakhir karena "
                                        "stok tidak lagi ditahan. Silakan "
                                        "ulangi dari keranjang."),
                            "flash_category": "warning",
                        }

                    logger.info(
                        f"Pengguna {user_id} memiliki pesanan tertunda "
                        f"{pending_order['id']}. Mengarahkan ke pembayaran."
                    )
                    return {
                        "success": False,
                        "redirect": url_for(
                            "purchase.payment_page",
                            order_id=pending_order["id"]
                        ),
                        "message": ("Anda memiliki pesanan yang belum dibayar. "
                                    "Silakan selesaikan pembayaran."),
                        "flash_category": "info",
                    }

                if not checkout_validation_service.validate_user_address(user):
                    logger.warning(
                        f"Checkout gagal untuk pengguna {user_id}: Alamat "
                        f"pengiriman belum lengkap."
                    )
                    return {
                        "success": False,
                        "redirect": url_for("purchase.edit_address"),
                        "message": ("Alamat pengiriman belum lengkap. Mohon "
                                    "perbarui di profil Anda."),
                        "flash_category": "danger",
                    }

                shipping_details = {
                    "name": user.get("username"),
                    "email": user.get("email"),
                    "phone": user.get("phone"),
                    "address1": user.get("address_line_1"),
                    "address2": user.get("address_line_2", ""),
                    "city": user.get("city"),
                    "province": user.get("province"),
                    "postal_code": user.get("postal_code"),
                }
                logger.debug(
                    f"Detail pengiriman pengguna {user_id}: {shipping_details}"
                )

            else:
                if not guest_cart_json or guest_cart_json == "{}":
                    logger.warning(
                        f"Checkout tamu gagal: Data keranjang kosong. "
                        f"Session ID: {session_id}"
                    )
                    return {
                        "success": False,
                        "redirect": url_for("purchase.cart_page"),
                        "message": "Keranjang Anda kosong.",
                        "flash_category": "danger",
                    }

                try:
                    cart_data = json.loads(guest_cart_json)
                    logger.debug(f"Data keranjang tamu dimuat: {cart_data}")

                except json.JSONDecodeError:
                    logger.error(
                        f"Checkout tamu gagal: JSON cart_data tidak valid. "
                        f"Session ID: {session_id}",
                        exc_info=True,
                    )
                    return {
                        "success": False,
                        "redirect": url_for("purchase.cart_page"),
                        "message": "Data keranjang tidak valid.",
                        "flash_category": "danger",
                    }

                email_for_order: Optional[str] = form_data.get("email")

                if not email_for_order:
                    logger.warning(
                        f"Checkout tamu gagal: Email tidak diisi. "
                        f"Session ID: {session_id}"
                    )
                    return {
                        "success": False,
                        "redirect": url_for("purchase.checkout"),
                        "message": "Email wajib diisi untuk checkout.",
                        "flash_category": "danger",
                    }

                if checkout_validation_service.check_guest_email_exists(
                    email_for_order
                ):
                    logger.warning(
                        f"Checkout tamu gagal: Email {email_for_order} "
                        f"sudah terdaftar. Session ID: {session_id}"
                    )
                    return {
                        "success": False,
                        "redirect": url_for(
                            "auth.login", next=url_for("purchase.checkout")
                        ),
                        "message": ("Email sudah terdaftar. Silakan login "
                                    "untuk melanjutkan."),
                        "flash_category": "danger",
                    }

                shipping_details = {
                    "name": form_data["full_name"],
                    "email": email_for_order,
                    "phone": form_data["phone"],
                    "address1": form_data["address_line_1"],
                    "address2": form_data.get("address_line_2", ""),
                    "city": form_data["city"],
                    "province": form_data["province"],
                    "postal_code": form_data["postal_code"],
                }
                session["guest_order_details"] = {
                    **shipping_details,
                }
                logger.debug(
                    f"Detail pengiriman tamu {session_id}: {shipping_details}"
                )

            payment_method: str = form_data["payment_method"]
            voucher_code: Optional[str] = (
                form_data.get("voucher_code") or None
            )
            user_voucher_id_str: Optional[str] = (
                form_data.get("user_voucher_id") or None
            )

            try:
                shipping_cost: float = float(form_data.get("shipping_cost", 0))

            except ValueError:
                logger.warning(
                    f"Nilai shipping_cost tidak valid: "
                    f"{form_data.get('shipping_cost')}. Diubah ke 0."
                )
                shipping_cost = 0.0

            logger.info(
                f"Membuat pesanan untuk {user_log_id}. "
                f"Metode: {payment_method}, Voucher: {voucher_code}, "
                f"UserVoucherID: {user_voucher_id_str}, "
                f"Pengiriman: {shipping_cost}"
            )
            result: Dict[str, Any] = order_creation_service.create_order(
                user_id=user_id,
                session_id=session_id if not user_id else None,
                shipping_details=shipping_details,
                payment_method=payment_method,
                voucher_code=voucher_code,
                user_voucher_id_str=user_voucher_id_str,
                shipping_cost=shipping_cost,
            )

            if result["success"]:
                order_id: int = result["order_id"]
                logger.info(
                    f"Pesanan #{order_id} berhasil dibuat untuk {user_log_id}."
                )

                if not user_id:
                    session["guest_order_id"] = order_id

                if payment_method == "COD":
                    return {
                        "success": True,
                        "redirect": url_for("purchase.order_success"),
                        "message": f"Pesanan #{order_id} (COD) berhasil dibuat!",
                        "flash_category": "success",
                    }
                else:
                    logger.info(
                        f"Mengarahkan {user_log_id} ke pembayaran untuk "
                        f"pesanan #{order_id}"
                    )
                    return {
                        "success": True,
                        "redirect": url_for(
                            "purchase.payment_page", order_id=order_id
                        ),
                    }

            else:
                logger.error(
                    f"Pembuatan pesanan gagal untuk {user_log_id}. Alasan: "
                    f"{result.get('message', 'Kesalahan tidak diketahui')}"
                )
                return {
                    "success": False,
                    "redirect": url_for("purchase.cart_page"),
                    "message": result.get("message", "Gagal membuat pesanan."),
                    "flash_category": "danger",
                }

        except (mysql.connector.Error, DatabaseException) as db_err:
            logger.error(
                f"Kesalahan database selama checkout untuk {user_log_id}: "
                f"{db_err}",
                exc_info=True,
            )
            return {
                "success": False,
                "redirect": url_for("purchase.cart_page"),
                "message": "Terjadi kesalahan database saat memproses checkout.",
                "flash_category": "danger",
            }

        except ValidationError as ve:
            logger.warning(
                f"Validasi gagal saat checkout untuk {user_log_id}: {ve}"
            )
            return {
                "success": False,
                "redirect": url_for("purchase.cart_page"),
                "message": str(ve),
                "flash_category": "danger",
            }

        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga selama checkout untuk {user_log_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "redirect": url_for("purchase.cart_page"),
                "message": "Terjadi kesalahan tak terduga saat checkout.",
                "flash_category": "danger",
            }

checkout_service = CheckoutService()