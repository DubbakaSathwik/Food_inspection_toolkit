"""Uniform error format: {"error": {"code": str, "message": str, "fields": {...}?}}."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError, PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("crate_scan.errors")


class AppError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields


def not_found(what: str = "Resource") -> AppError:
    return AppError(404, "not_found", f"{what} not found.")


def forbidden(message: str = "You do not have permission to do this.") -> AppError:
    return AppError(403, "forbidden", message)


def bad_request(message: str, fields: dict[str, str] | None = None) -> AppError:
    return AppError(400, "bad_request", message, fields)


def conflict(message: str) -> AppError:
    return AppError(409, "conflict", message)


def _body(code: str, message: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if fields:
        err["fields"] = fields
    return {"error": err}


_STATUS_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    429: "rate_limited",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message, exc.fields), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for e in exc.errors():
            loc = [str(p) for p in e.get("loc", ()) if p not in ("body", "query", "path")]
            fields[".".join(loc) or "request"] = str(e.get("msg", "Invalid value"))
        return JSONResponse(
            _body("validation_error", "Some values are invalid.", fields), status_code=422
        )

    @app.exception_handler(ValidationError)
    async def _model_validation(_: Request, exc: ValidationError) -> JSONResponse:
        fields = {
            ".".join(str(p) for p in e["loc"]) or "request": str(e["msg"]) for e in exc.errors()
        }
        return JSONResponse(
            _body("validation_error", "Some values are invalid.", fields), status_code=422
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "error")
        msg = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(_body(code, msg), status_code=exc.status_code)

    @app.exception_handler(DuplicateKeyError)
    async def _dup(_: Request, exc: DuplicateKeyError) -> JSONResponse:
        return JSONResponse(_body("conflict", "This record already exists."), status_code=409)

    @app.exception_handler(PyMongoError)
    async def _db(_: Request, exc: PyMongoError) -> JSONResponse:
        log.error("database error: %s", type(exc).__name__)
        return JSONResponse(
            _body("database_unavailable", "The database is temporarily unavailable."),
            status_code=503,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error: %s", type(exc).__name__)
        return JSONResponse(_body("internal_error", "Something went wrong."), status_code=500)
