from flask import jsonify
from flask.wrappers import Response


def create_json_error_response(
    status_code: int, error_type: str, message: str
) -> Response:
    response_data: dict[str, dict[str, str]] = {
        "error": {"type": error_type, "message": message}
    }
    response: Response = jsonify(response_data)
    response.status_code = status_code
    return response


def bad_request(message: str = "Permintaan Buruk") -> Response:
    return create_json_error_response(400, "BadRequest", message)


def unauthorized(message: str = "Tidak Sah") -> Response:
    return create_json_error_response(401, "Unauthorized", message)


def forbidden(message: str = "Dilarang") -> Response:
    return create_json_error_response(403, "Forbidden", message)


def not_found(message: str = "Tidak Ditemukan") -> Response:
    return create_json_error_response(404, "NotFound", message)


def internal_server_error(
    message: str = "Kesalahan Server Internal",
) -> Response:
    return create_json_error_response(500, "InternalServerError", message)


def service_unavailable(message: str = "Layanan Tidak Tersedia") -> Response:
    return create_json_error_response(503, "ServiceUnavailable", message)