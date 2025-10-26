from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def get_date_range(
    period_str: str,
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Tuple[str, str]:
    logger.debug(
        f"Menghitung rentang tanggal untuk periode: {period_str}, "
        f"custom_start: {custom_start}, custom_end: {custom_end}"
    )

    if custom_start and custom_end:
        start_date_str: str = f"{custom_start} 00:00:00"
        end_date_str: str = f"{custom_end} 23:59:59"
        logger.debug(
            f"Menggunakan rentang tanggal kustom: {start_date_str} "
            f"hingga {end_date_str}"
        )
        
        return start_date_str, end_date_str

    today: datetime = datetime.now()

    if period_str == "last_30_days":
        start_date: datetime = today - timedelta(days=29)
        end_date: datetime = today

    elif period_str == "this_month":
        start_date = today.replace(day=1)
        end_date = today

    else:
        start_date = today - timedelta(days=6)
        end_date = today

    start_date_str = start_date.strftime("%Y-%m-%d 00:00:00")
    end_date_str = end_date.strftime("%Y-%m-%d 23:59:59")

    logger.debug(
        f"Rentang tanggal dihitung: {start_date_str} hingga {end_date_str} "
        f"berdasarkan periode '{period_str}'"
    )

    return start_date_str, end_date_str