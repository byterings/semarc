import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}


class ApiError(Exception):
    """An API error rendered as an `error` object with code, message and optional details."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, list[str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
        self.headers = headers or {}

    @classmethod
    def unauthorized(cls, message: str = "Authentication required.") -> "ApiError":
        return cls(401, "unauthorized", message)

    @classmethod
    def forbidden(cls, message: str) -> "ApiError":
        return cls(403, "forbidden", message)

    @classmethod
    def not_found(cls, message: str = "Resource not found.") -> "ApiError":
        return cls(404, "not_found", message)

    @classmethod
    def conflict(cls, message: str, details: dict[str, list[str]] | None = None) -> "ApiError":
        return cls(409, "conflict", message, details)

    @classmethod
    def validation(cls, details: dict[str, list[str]]) -> "ApiError":
        return cls(422, "validation_failed", "The given data was invalid.", details)

    @classmethod
    def not_implemented(cls, message: str) -> "ApiError":
        return cls(501, "not_implemented", message)


def error_response(
    status: int, code: str, message: str, details: dict | None = None, headers: dict[str, str] | None = None
) -> JSONResponse:
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse({"error": error}, status_code=status, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
        return error_response(error.status, error.code, error.message, error.details, error.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        details: dict[str, list[str]] = {}
        for item in error.errors():
            if item["type"] == "json_invalid":
                return error_response(400, "bad_request", "Request body must be valid JSON.")
            location = [str(part) for part in item["loc"] if part not in {"body", "query", "path"}]
            field = ".".join(location) or "body"
            if item["type"] == "missing":
                message = f"{field} is required"
            elif item["type"] == "value_error":
                message = f"{field} " + item["msg"].removeprefix("Value error, ")
            else:
                message = item["msg"]
            details.setdefault(field, []).append(message)
        return error_response(422, "validation_failed", "The given data was invalid.", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
        code = HTTP_ERROR_CODES.get(error.status_code, "http_error")
        message = "Route not found." if error.status_code == 404 else str(error.detail)
        return error_response(error.status_code, code, message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=error)
        return error_response(500, "internal_error", "Internal server error.")
