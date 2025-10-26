from typing import Any, Dict, List, Tuple, Union

from flask import Response, flash, jsonify, render_template, request

from app.core.db import get_content
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException,
    RecordNotFoundError,
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.voucher_service import voucher_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/vouchers", methods=["GET", "POST"])
@admin_required
def admin_vouchers() -> Union[str, Response, Tuple[Response, int]]:
    if request.method == "POST":
        code: str = request.form.get("code")
        v_type: str = request.form.get("type")
        value: str = request.form.get("value")
        min_purchase: str = request.form.get("min_purchase_amount")
        max_uses: str = request.form.get("max_uses")
        logger.debug(
            f"Route: Menerima permintaan POST untuk menambah voucher. Kode: {code}"
        )

        try:
            result: Dict[str, Any] = voucher_service.add_voucher(
                code, v_type, value, min_purchase, max_uses
            )

            if result.get("success"):
                logger.info(
                    f"Route: Voucher '{code}' berhasil ditambahkan via service."
                )
                html: str = render_template(
                    "admin/partials/_voucher_row.html", voucher=result["data"]
                )
                result["html"] = html
                return jsonify(result), 200
            
            else:
                logger.warning(
                    f"Route: Gagal menambahkan voucher '{code}' via service. "
                    f"Alasan: {result.get('message')}"
                )
                status_code: int = (
                    409 if "sudah terdaftar" in result.get("message", "") else 400
                )
                return jsonify(result), status_code

        except ValidationError as ve:
            logger.warning(f"Kesalahan validasi saat menambahkan voucher '{code}': {ve}")
            return jsonify({"success": False, "message": str(ve)}), 400
        
        except DatabaseException as de:
            logger.error(
                f"Kesalahan database saat menambahkan voucher '{code}': {de}",
                exc_info=True,
            )
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan database."}
                ),
                500,
            )
        
        except ServiceLogicError as sle:
            logger.error(
                f"Kesalahan logika servis saat menambahkan voucher '{code}': {sle}",
                exc_info=True,
            )
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan pada server."}
                ),
                500,
            )
        
        except Exception as e:
            logger.error(
                f"Route: Terjadi kesalahan tak terduga saat memanggil "
                f"service add_voucher untuk kode '{code}': {e}",
                exc_info=True,
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Gagal menambahkan voucher karena "
                        "kesalahan server.",
                    }
                ),
                500,
            )

    logger.debug(
        "Route: Permintaan GET ke /vouchers. Mengambil data voucher via service..."
    )

    try:
        vouchers: List[Dict[str, Any]] = voucher_service.get_all_vouchers()
        logger.info(
            f"Route: Berhasil mengambil {len(vouchers)} data voucher dari service."
        )
        return render_template(
            "admin/manage_vouchers.html", vouchers=vouchers, content=get_content()
        )
    
    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Route: Kesalahan saat mengambil voucher dari service: {service_err}",
            exc_info=True,
        )
        flash("Gagal memuat halaman voucher.", "danger")
        return render_template(
            "admin/manage_vouchers.html", vouchers=[], content=get_content()
        )
    
    except Exception as e:
        logger.error(
            f"Route: Kesalahan tak terduga saat mengambil voucher dari service: {e}",
            exc_info=True,
        )
        flash("Gagal memuat halaman voucher.", "danger")
        return render_template(
            "admin/manage_vouchers.html", vouchers=[], content=get_content()
        )


@admin_bp.route("/vouchers/delete/<int:id>", methods=["POST"])
@admin_required
def delete_voucher(id: int) -> Tuple[Response, int]:
    logger.debug(
        f"Route: Menerima permintaan POST untuk menghapus voucher ID: {id}"
    )
    try:
        result: Dict[str, Any] = voucher_service.delete_voucher_by_id(id)

        if result.get("success"):
            logger.info(
                f"Route: Voucher ID {id} berhasil dihapus via service."
            )
            return jsonify(result), 200
        
        else:
            logger.warning(
                f"Route: Gagal menghapus voucher ID {id} via service. "
                f"Alasan: {result.get('message')}"
            )
            status_code: int = (
                404 if "tidak ditemukan" in result.get("message", "") else 500
            )
            return jsonify(result), status_code
        
    except RecordNotFoundError as rnfe:
        logger.warning(f"Hapus gagal: Voucher ID {id} tidak ditemukan: {rnfe}")
        return jsonify({"success": False, "message": str(rnfe)}), 404
    
    except DatabaseException as de:
        logger.error(
            f"Kesalahan database saat menghapus voucher ID {id}: {de}",
            exc_info=True,
        )
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan database."}
            ),
            500,
        )
    
    except ServiceLogicError as sle:
        logger.error(
            f"Kesalahan logika servis saat menghapus voucher ID {id}: {sle}",
            exc_info=True,
        )

        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan pada server."}
            ),
            500,
        )
    
    except Exception as e:
        logger.error(
            f"Route: Terjadi kesalahan tak terduga saat memanggil "
            f"service delete_voucher_by_id untuk ID {id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Gagal menghapus voucher karena "
                    "kesalahan server.",
                }
            ),
            500,
        )


@admin_bp.route("/vouchers/toggle/<int:id>", methods=["POST"])
@admin_required
def toggle_voucher(id: int) -> Tuple[Response, int]:
    logger.debug(
        f"Route: Menerima permintaan POST untuk mengubah status voucher ID: {id}"
    )

    try:
        result: Dict[str, Any] = voucher_service.toggle_voucher_status(id)

        if result.get("success"):
            logger.info(
                f"Route: Status voucher ID {id} berhasil diubah via service."
            )
            return jsonify(result), 200
        
        else:
            logger.warning(
                f"Route: Gagal mengubah status voucher ID {id} via service. "
                f"Alasan: {result.get('message')}"
            )
            status_code: int = (
                404 if "tidak ditemukan" in result.get("message", "") else 500
            )
            return jsonify(result), status_code
        
    except RecordNotFoundError as rnfe:
        logger.warning(
            f"Toggle gagal: Voucher ID {id} tidak ditemukan: {rnfe}"
        )
        return jsonify({"success": False, "message": str(rnfe)}), 404
    
    except DatabaseException as de:
        logger.error(
            f"Kesalahan database saat mengubah status voucher ID {id}: {de}",
            exc_info=True,
        )
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan database."}
            ),
            500,
        )
    
    except ServiceLogicError as sle:
        logger.error(
            f"Kesalahan logika servis saat mengubah status voucher ID {id}: {sle}",
            exc_info=True,
        )
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan pada server."}
            ),
            500,
        )
    
    except Exception as e:
        logger.error(
            f"Route: Terjadi kesalahan tak terduga saat memanggil "
            f"service toggle_voucher_status untuk ID {id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Gagal mengubah status voucher karena "
                    "kesalahan server.",
                }
            ),
            500,
        )