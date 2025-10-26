import traceback
from types import TracebackType
from typing import Tuple, Type

from flask import current_app, request

ExcInfo = Tuple[Type[BaseException], BaseException, TracebackType]


def format_traceback(exc_info: ExcInfo) -> str:
    return "".join(
        traceback.format_exception(exc_info[0], exc_info[1], exc_info[2])
    )


def log_exception(
    exception: Exception, level: str = "error"
) -> None:
    logger = current_app.logger
    tb: str = traceback.format_exc()
    log_message: str = (
        f"Terjadi eksepsi: {type(exception).__name__}: {exception}\n"
        f"URL: {request.url}\nMetode: {request.method}\n{tb}"
    )

    if level == "critical":
        logger.critical(log_message)
    elif level == "error":
        logger.error(log_message)
    elif level == "warning":
        logger.warning(log_message)
    elif level == "info":
        logger.info(log_message)
    else:
        logger.debug(log_message)