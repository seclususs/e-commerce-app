from typing import Optional

from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response


class APIException(HTTPException):
    code: int = 500
    description: str = "Terjadi kesalahan pada API."

    def __init__(
        self,
        description: Optional[str] = None,
        response: Optional[Response] = None,
        code: Optional[int] = None,
    ) -> None:
        
        if description is not None:
            self.description = description

        if code is not None:
            self.code = code
            
        super().__init__(description=self.description, response=response)


class ValidationError(APIException):
    code: int = 400
    description: str = "Data yang diberikan tidak valid."


class AuthError(APIException):
    code: int = 401
    description: str = "Autentikasi gagal."


class PermissionDeniedError(APIException):
    code: int = 403
    description: str = "Anda tidak memiliki izin untuk mengakses sumber daya ini."


class NotFoundError(APIException):
    code: int = 404
    description: str = "Sumber daya yang diminta tidak ditemukan."


class RateLimitError(APIException):
    code: int = 429
    description: str = "Terlalu banyak permintaan."