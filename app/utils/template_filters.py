import json
from datetime import datetime, timedelta
from typing import Any, List, Optional, Union
from decimal import Decimal, ROUND_HALF_UP

from flask import Flask

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def format_rupiah(value: Any) -> str:

    try:
        val_decimal = Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        formatted_string = f"{val_decimal:,.0f}".replace(",", ".")
        return f"Rp {formatted_string}"

    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(
            f"Tidak dapat memformat nilai sebagai Rupiah: {value}, Error: {e}",
            exc_info=False,
        )
        return "Rp 0"


def format_percentage(part: Any, whole: Any) -> int:

    try:
        part_float: float = float(part)
        whole_float: float = float(whole)

        if whole_float == 0:
            return 0

        percentage: int = round(
            100 * (whole_float - part_float) / whole_float
        )
        return max(0, percentage)

    except (ValueError, TypeError):
        logger.debug(
            f"Tidak dapat menghitung persentase untuk bagian={part}, "
            f"keseluruhan={whole}",
            exc_info=False,
        )
        return 0


def fromjson_safe_filter(json_str: Optional[str]) -> list:

    try:
        if not json_str:
            return []
        return json.loads(json_str)

    except (json.JSONDecodeError, TypeError):
        logger.warning(
            f"Gagal mendekode string JSON di filter template: {json_str}",
            exc_info=False,
        )
        return []


def tojson_safe_filter(obj: Any) -> str:

    try:
        return json.dumps(obj)

    except TypeError:
        logger.warning(
            f"Gagal mengkode objek ke JSON di filter template: {type(obj)}",
            exc_info=False,
        )
        return "null"


def split_filter(value: Any, delimiter: str) -> Union[Any, List[str]]:
    if not isinstance(value, str):
        return value
    return value.split(delimiter)


def status_translate_filter(status_en: str) -> str:
    status_map: dict[str, str] = {
        "Pending": "Menunggu Pembayaran",
        "Processing": "Diproses",
        "Shipped": "Dikirim",
        "Completed": "Selesai",
        "Cancelled": "Dibatalkan",
        "Menunggu Pembayaran": "Menunggu Pembayaran",
        "Diproses": "Diproses",
        "Dikirim": "Dikirim",
        "Selesai": "Selesai",
        "Dibatalkan": "Dibatalkan",
        "Pesanan Dibuat": "Pesanan Dibuat",
    }
    return status_map.get(status_en, status_en)


def status_class_filter(status_en: str) -> str:
    class_map: dict[str, str] = {
        "Pending": "pending",
        "Processing": "processing",
        "Shipped": "shipped",
        "Completed": "completed",
        "Cancelled": "cancelled",
        "Menunggu Pembayaran": "pending",
        "Diproses": "processing",
        "Dikirim": "shipped",
        "Selesai": "completed",
        "Dibatalkan": "cancelled",
        "Pesanan Dibuat": "pending",
    }
    return class_map.get(status_en, "pending")


def datetime_from_string_filter(
    date_input: Union[str, datetime, None]
) -> Optional[datetime]:

    if isinstance(date_input, datetime):
        return date_input

    if not date_input or not isinstance(date_input, str):
        return None

    date_string: str = str(date_input)

    try:
        return datetime.fromisoformat(date_string.split(".")[0])

    except (ValueError, TypeError):

        try:
            return datetime.strptime(date_string.split(" ")[0], "%Y-%m-%d")

        except (ValueError, TypeError):
            logger.error(
                f"Kesalahan saat mem-parsing string tanggal di "
                f"filter template: {date_string}",
                exc_info=False,
            )
            return datetime.now()


def add_days_filter(
    dt: Union[str, datetime, None], days: int
) -> Optional[datetime]:
    dt_obj: Optional[datetime] = datetime_from_string_filter(dt)

    if isinstance(dt_obj, datetime) and isinstance(days, int):
        return dt_obj + timedelta(days=days)

    return dt_obj


def register_template_filters(app: Flask) -> None:
    logger.debug("Mendaftarkan filter template kustom.")

    app.template_filter("rupiah")(format_rupiah)
    app.template_filter("percentage")(format_percentage)
    app.template_filter("tojson_safe")(tojson_safe_filter)
    app.template_filter("fromjson_safe")(fromjson_safe_filter)
    app.template_filter("split")(split_filter)
    app.template_filter("status_translate")(status_translate_filter)
    app.template_filter("status_class")(status_class_filter)
    app.template_filter("datetime_from_string")(
        datetime_from_string_filter
    )
    app.template_filter("add_days")(add_days_filter)
    logger.info("Filter template kustom berhasil didaftarkan.")