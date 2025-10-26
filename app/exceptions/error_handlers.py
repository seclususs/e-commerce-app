from flask import Flask
from flask.wrappers import Response
from werkzeug.exceptions import (
    BadRequest,
    Forbidden,
    HTTPException,
    InternalServerError,
    NotFound,
    Unauthorized,
)

from app.exceptions import http_error_responses as error_responses
from app.exceptions.api_exceptions import APIException
from app.utils.error_utils import log_exception


def handle_not_found(error: NotFound) -> Response:
    log_exception(error, level="warning")
    return error_responses.not_found(error.description)


def handle_bad_request(error: BadRequest) -> Response:
    log_exception(error, level="warning")
    return error_responses.bad_request(error.description)


def handle_unauthorized(error: Unauthorized) -> Response:
    log_exception(error, level="warning")
    return error_responses.unauthorized(error.description)


def handle_forbidden(error: Forbidden) -> Response:
    log_exception(error, level="warning")
    return error_responses.forbidden(error.description)


def handle_api_exception(error: APIException) -> Response:
    log_exception(error, level="warning")
    return error_responses.create_json_error_response(
        error.code, error.__class__.__name__, error.description
    )


def handle_generic_http_exception(error: HTTPException) -> Response:
    log_exception(error, level="error")
    return error_responses.create_json_error_response(
        error.code, error.__class__.__name__, error.description
    )


def handle_internal_server_error(error: InternalServerError) -> Response:
    log_exception(error, level="error")
    return error_responses.internal_server_error(
        "Terjadi kesalahan internal pada server."
    )


def handle_generic_exception(error: Exception) -> Response:
    log_exception(error, level="critical")
    return error_responses.internal_server_error(
        "Terjadi kesalahan tak terduga pada server."
    )


def register_error_handlers(app: Flask) -> None:
    app.register_error_handler(NotFound, handle_not_found)
    app.register_error_handler(BadRequest, handle_bad_request)
    app.register_error_handler(Unauthorized, handle_unauthorized)
    app.register_error_handler(Forbidden, handle_forbidden)
    app.register_error_handler(APIException, handle_api_exception)
    app.register_error_handler(HTTPException, handle_generic_http_exception)
    app.register_error_handler(InternalServerError, handle_internal_server_error)
    app.register_error_handler(Exception, handle_generic_exception)
    app.logger.info("Penangan error berhasil didaftarkan.")