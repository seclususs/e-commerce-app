import uuid
from typing import Any, Dict, List, Tuple, Optional

from flask import Response, jsonify, request, session

from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException, RecordNotFoundError
from app.exceptions.service_exceptions import OutOfStockError, ServiceLogicError
from app.services.orders.cart_service import cart_service
from app.services.orders.stock_service import stock_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/cart", methods=["POST"])
def get_guest_cart_items() -> Response:
    data: Dict[str, Any] | None = request.get_json()
    cart_items: List[Dict[str, Any]] | None = (
        data.get("cart_items") if data else None
    )

    logger.debug(f"Mengambil detail keranjang tamu untuk item: {cart_items}")
    
    if not cart_items:
        logger.info("Keranjang tamu kosong atau data tidak valid.")
        return jsonify([])

    try:
        detailed_items: List[Dict[str, Any]] = (
            cart_service.get_guest_cart_details(cart_items)
        )
        logger.info(
            "Detail keranjang tamu berhasil diambil. "
            f"Jumlah item: {len(detailed_items)}"
        )
        return jsonify(detailed_items)

    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            "Terjadi kesalahan service/DB saat mengambil detail "
            f"keranjang tamu: {e}",
            exc_info=True,
        )
        return jsonify(
            {"success": False, "message": "Gagal mengambil detail keranjang."}
            ), 500

    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat mengambil detail "
            f"keranjang tamu: {e}",
            exc_info=True,
        )
        return jsonify(
            {"success": False, "message": "Gagal mengambil detail keranjang."}
            ), 500


@api_bp.route("/user-cart", methods=["GET"])
@login_required
def get_user_cart() -> Response:
    user_id: Optional[int] = session.get("user_id")
    if not user_id:
        logger.warning("API: /user-cart GET ditolak. Pengguna tidak login.")
        return jsonify({"success": False, "message": "Otentikasi diperlukan."}), 401
    
    logger.debug(f"Mengambil detail keranjang untuk user_id: {user_id}")

    try:
        cart_data: Dict[str, Any] = cart_service.get_cart_details(user_id)
        logger.info(
            f"Detail keranjang berhasil diambil untuk user_id: {user_id}. "
            f"Jumlah item: {len(cart_data.get('items', []))}"
        )
        return jsonify(cart_data)

    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            "Terjadi kesalahan service/DB saat mengambil keranjang user "
            f"{user_id}: {e}",
            exc_info=True,
        )
        return jsonify(
            {"success": False, "message": "Gagal mengambil detail keranjang."}
            ), 500

    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat mengambil keranjang user "
            f"{user_id}: {e}",
            exc_info=True,
        )
        return jsonify(
            {"success": False, "message": "Gagal mengambil detail keranjang."}
            ), 500


@api_bp.route("/user-cart", methods=["POST"])
@login_required
def add_to_user_cart() -> Tuple[Response, int]:
    user_id: Optional[int] = session.get("user_id")
    if not user_id:
        logger.warning("API: /user-cart POST ditolak. Pengguna tidak login.")
        return jsonify(
            {"success": False, "message": "Otentikasi diperlukan."}
            ), 401

    data: Dict[str, Any] | None = request.get_json()
    if not data:
        return jsonify(
            {"success": False, "message": "Data JSON tidak valid."}
            ), 400

    product_id: int | None = data.get("product_id")
    variant_id_input: Any = data.get("variant_id")
    variant_id: Optional[int] = None
    if variant_id_input is not None:

        try:
            variant_id = int(variant_id_input)

        except (ValueError, TypeError):
            logger.warning(
                f"Input variant_id tidak valid '{variant_id_input}', "
                f"akan diabaikan."
            )
            variant_id = None

    quantity: int = data.get("quantity", 1)
    
    logger.debug(
        f"Menambahkan item ke keranjang untuk user_id: {user_id}. "
        f"Produk: {product_id}, Varian: {variant_id}, Jumlah: {quantity}"
    )

    if not product_id or not isinstance(quantity, int) or quantity <= 0:
        logger.warning(
            f"Permintaan penambahan item tidak valid untuk user_id: {user_id}. "
            f"Data: {data}"
        )
        return jsonify({"success": False, "message": "Data tidak valid."}), 400

    try:
        result: Dict[str, Any] = cart_service.add_to_cart(
            user_id, product_id, quantity, variant_id
        )

        if result["success"]:
            logger.info(
                f"Item berhasil ditambahkan untuk user_id: {user_id}. "
                f"Produk: {product_id}, Varian: {variant_id}"
            )
            return jsonify(result), 200
        
        else:
            logger.warning(
                f"Gagal menambahkan item untuk user_id: {user_id}. "
                f"Alasan: {result['message']}"
            )
            message: str = result.get("message", "")
            if "Stok" in message:
                return jsonify({"success": False, "message": message}), 400
            elif "Produk tidak ditemukan" in message:
                return jsonify({"success": False, "message": message}), 404
            elif "pilih ukuran" in message:
                return jsonify({"success": False, "message": message}), 400
            else:
                return jsonify({"success": False, "message": message}), 500

    except (
        ValidationError, RecordNotFoundError, OutOfStockError
    ) as e:
        logger.error(
            f"Error caught in add_to_user_cart for user {user_id}: {e}",
            exc_info=True
        )
        status_code = 400
        if isinstance(e, RecordNotFoundError):
            status_code = 404
        return jsonify({"success": False, "message": str(e)}), status_code
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error caught in add_to_user_cart for user {user_id}: {e}",
            exc_info=True
        )
        return jsonify(
            {"success": False, "message": "Gagal menambahkan item ke keranjang."}
            ), 500
    
    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat menambahkan item ke keranjang "
            f"user {user_id}: {e}", exc_info=True
        )
        return jsonify(
            {"success": False, "message": "Gagal menambahkan item ke keranjang."}
            ), 500


@api_bp.route("/user-cart/<int:product_id>/<variant_id_str>", methods=["PUT"])
@login_required
def update_user_cart_item(
    product_id: int, variant_id_str: str
) -> Tuple[Response, int]:
    user_id: Optional[int] = session.get("user_id")
    if not user_id:
        logger.warning("API: /user-cart PUT ditolak. Pengguna tidak login.")
        return jsonify(
            {"success": False, "message": "Otentikasi diperlukan."}
            ), 401

    variant_id: Optional[int] = None
    if variant_id_str.lower() != 'null':

        try:
            variant_id = int(variant_id_str)
        except ValueError:
            logger.warning(
                f"String variant_id tidak valid '{variant_id_str}' "
                f"diterima, dianggap tidak ada varian."
            )
            variant_id = None

    data: Dict[str, Any] | None = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Data JSON tidak valid."}), 400

    quantity: int | None = data.get("quantity")
    
    logger.debug(
        f"Memperbarui item keranjang untuk user_id: {user_id}. "
        f"Produk: {product_id}, Varian: {variant_id}, "
        f"Jumlah baru: {quantity}"
    )
    if quantity is None or not isinstance(quantity, int):
        logger.warning(
            f"Permintaan pembaruan keranjang tidak valid untuk "
            f"user_id: {user_id}. Data: {data}"
        )
        return jsonify({"success": False, "message": "Kuantitas tidak valid."}), 400

    try:
        result: Dict[str, Any] = cart_service.update_cart_item(
            user_id, product_id, quantity, variant_id
        )
        if result["success"]:
            logger.info(
                f"Item keranjang berhasil diperbarui untuk user_id: {user_id}. "
                f"Produk: {product_id}, Varian: {variant_id}, "
                f"Kuantitas: {quantity}"
            )
            return jsonify(result), 200
        else:
            logger.warning(
                f"Gagal memperbarui item keranjang untuk user_id: {user_id}. "
                f"Alasan: {result.get('message', 'Tidak diketahui')}"
            )
            if "Stok" in result.get("message", ""):
                return jsonify({"success": False, "message": result["message"]}), 400
            else:
                return jsonify({"success": False, "message": result.get("message", "Gagal memperbarui item.")}), 500

    except OutOfStockError as e:
        logger.error(
            f"Error caught in update_user_cart_item for user {user_id}: {e}",
            exc_info=True
        )
        return jsonify({"success": False, "message": str(e)}), 400
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error caught in update_user_cart_item for user {user_id}: {e}",
            exc_info=True
        )
        return jsonify({"success": False, "message": "Gagal memperbarui item keranjang."}), 500
    
    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat memperbarui item keranjang "
            f"user {user_id}: {e}", exc_info=True
        )
        return jsonify({"success": False, "message": "Gagal memperbarui item keranjang."}), 500


@api_bp.route("/user-cart/merge", methods=["POST"])
@login_required
def merge_cart() -> Tuple[Response, int] | Response:
    user_id: Optional[int] = session.get("user_id")
    if not user_id:
        logger.warning("API: /user-cart/merge ditolak. Pengguna tidak login.")
        return jsonify(
            {"success": False, "message": "Otentikasi diperlukan."}
            ), 401

    local_cart_data: Dict[str, Any] | None = request.get_json()
    local_cart: Dict[str, Any] | None = (
        local_cart_data.get("local_cart") if local_cart_data else None
    )
    
    logger.debug(
        f"Mencoba menggabungkan keranjang lokal untuk user_id: {user_id}. "
        "Kunci keranjang lokal: "
        f"{list(local_cart.keys()) if local_cart else 'None'}"
    )

    if not local_cart:
        logger.info(
            f"Tidak ada keranjang lokal untuk digabung untuk user_id: {user_id}"
        )
        return jsonify({
            "success": True,
            "message": "Tidak ada keranjang lokal untuk digabung."
        })

    try:
        result: Dict[str, Any] = cart_service.merge_local_cart_to_db(
            user_id, local_cart
        )
        if result["success"]:
            logger.info(
                f"Keranjang lokal berhasil digabung untuk user_id: {user_id}"
            )
            return jsonify(result), 200
        
        else:
            logger.warning(
                f"Gagal menggabungkan keranjang lokal untuk user_id: {user_id}. "
                f"Alasan: {result['message']}"
            )
            return jsonify({"success": False, "message": result["message"]}), 500

    except (ValidationError, DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error caught in merge_cart for user {user_id}: {e}",
            exc_info=True
        )
        status_code = 500
        if isinstance(e, ValidationError):
            status_code = 400
        return jsonify({"success": False, "message": str(e)}), status_code
    
    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat menggabungkan keranjang "
            f"user {user_id}: {e}", exc_info=True
        )
        return jsonify(
            {"success": False, "message": "Gagal menyinkronkan keranjang."}
            ), 500


@api_bp.route("/checkout/prepare", methods=["POST"])
def prepare_guest_checkout() -> Tuple[Response, int]:
    if "user_id" in session:
        logger.warning(
            "Pengguna yang login mencoba mengakses endpoint checkout tamu."
        )
        return jsonify(
            {"success": False, "message": "Endpoint ini hanya untuk tamu."}
            ), 403

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        logger.info(
            f"session_id baru dibuat untuk checkout tamu: "
            f"{session['session_id']}"
        )

    session_id: str = session["session_id"]
    items_to_hold_data: Dict[str, Any] | None = request.get_json()
    items_to_hold: List[Dict[str, Any]] | None = (
        items_to_hold_data.get("items") if items_to_hold_data else None
    )
    logger.debug(
        f"Mempersiapkan checkout tamu untuk session_id: {session_id}. "
        f"Item: {items_to_hold}"
    )

    if not items_to_hold or not isinstance(items_to_hold, list):
        logger.warning(
            f"Data keranjang tidak valid untuk persiapan checkout tamu. "
            f"Session ID: {session_id}"
        )
        return jsonify(
            {"success": False, "message": "Data keranjang tidak valid."}
            ), 400

    formatted_items: List[Dict[str, Any]] = []

    try:
        for item in items_to_hold:
            variant_id: Optional[int] = item.get("variant_id")
            formatted_items.append({
                "id": item["id"],
                "name": item["name"],
                "size": item.get("size"),
                "variant_id": variant_id,
                "quantity": item["quantity"],
                "product_id": item["id"]
            })

    except KeyError as e:
        logger.error(
            f"Kunci data item keranjang tamu hilang: {e}. "
            f"Session ID: {session_id}", exc_info=True
        )
        return jsonify(
            {"success": False, "message": "Data item keranjang tidak lengkap."}
            ), 400

    try:
        hold_result: Dict[str, Any] = stock_service.hold_stock_for_checkout(
            None, session_id, formatted_items
        )

        if hold_result["success"]:
            logger.info(
                f"Stok berhasil ditahan untuk checkout tamu. "
                f"Session ID: {session_id}. "
                f"Kadaluarsa pada: {hold_result['expires_at']}"
            )
            return jsonify(hold_result), 200
        
        else:
            logger.warning(
                f"Gagal menahan stok untuk checkout tamu. "
                f"Session ID: {session_id}. Alasan: {hold_result['message']}"
            )
            if "Stok" in hold_result.get("message", ""):
                return jsonify(
                    {"success": False, "message": hold_result["message"]}
                    ), 400
            else:
                return jsonify(
                    {"success": False, "message": hold_result["message"]}
                    ), 500

    except (
        OutOfStockError, ValidationError
    ) as e:
        logger.error(
            f"Error caught in prepare_guest_checkout for session "
            f"{session_id}: {e}", exc_info=True
        )
        return jsonify({"success": False, "message": str(e)}), 400

    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error caught in prepare_guest_checkout for session "
            f"{session_id}: {e}", exc_info=True
        )
        return jsonify(
            {"success": False, "message": "Gagal memvalidasi stok."}
            ), 500
    
    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat menahan stok untuk checkout "
            f"tamu. Session ID: {session_id}: {e}", exc_info=True
        )
        return jsonify(
            {"success": False, "message": "Gagal memvalidasi stok."}
            ), 500