"""
ServiceOS — Global Exception Handlers
All unhandled exceptions are converted to RFC 7807 Problem Details.
No raw Python exceptions ever reach the client.
"""
import traceback
import uuid
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.base import make_problem, ProblemDetail, ValidationProblemDetail, ValidationErrorItem

logger = structlog.get_logger("exceptions")


class ServiceOSException(Exception):
    """
    Base exception for all ServiceOS domain errors.
    Raise this (or subclasses) from any engine — the handler converts to RFC 7807.
    """
    def __init__(
        self,
        error_code: str,
        detail: str,
        status_code: int | None = None,
        blocking_rule: str | None = None,
        resolution: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.detail = detail
        self.status_code = status_code
        self.blocking_rule = blocking_rule
        self.resolution = resolution
        self.context = context
        super().__init__(detail)


class NotFoundException(ServiceOSException):
    def __init__(self, resource: str, resource_id: str, tenant_id: str | None = None):
        super().__init__(
            error_code="NOT_FOUND",
            detail=f"{resource} '{resource_id}' not found.",
            resolution=f"Verify the {resource.lower()} ID and ensure it belongs to your tenant.",
            context={"resource": resource, "resource_id": resource_id, "tenant_id": tenant_id},
        )


class PermissionDeniedException(ServiceOSException):
    def __init__(self, required_role: str, current_role: str):
        super().__init__(
            error_code="PERMISSION_DENIED",
            detail=f"Role '{current_role}' cannot perform this action.",
            blocking_rule=f"required_role: {required_role}",
            resolution=f"Use a token with role: {required_role}.",
            context={"required_role": required_role, "current_role": current_role},
        )


class EngineDisabledException(ServiceOSException):
    def __init__(self, engine_id: str, tenant_id: str):
        super().__init__(
            error_code="ENGINE_DISABLED",
            detail=f"Engine '{engine_id}' is not enabled for tenant '{tenant_id}'.",
            blocking_rule=f"{engine_id}.is_enabled must be true",
            resolution="Enable this engine from tenant settings or contact your platform admin.",
            context={"engine_id": engine_id, "tenant_id": tenant_id},
        )


class InvalidTransitionException(ServiceOSException):
    def __init__(self, from_status: str, to_status: str, blocking_reason: str | None = None):
        super().__init__(
            error_code="INVALID_TRANSITION",
            detail=f"Cannot transition from '{from_status}' to '{to_status}'.",
            blocking_rule=blocking_reason or f"No valid path from {from_status} → {to_status}",
            resolution="Check the allowed_transitions field in the entity response for valid next steps.",
            context={"from_status": from_status, "to_status": to_status},
        )


class TenantSuspendedException(ServiceOSException):
    def __init__(self, tenant_id: str):
        super().__init__(
            error_code="TENANT_SUSPENDED",
            detail=f"Tenant '{tenant_id}' is suspended.",
            resolution="Contact platform support to reinstate your account.",
            context={"tenant_id": tenant_id},
        )


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def _problem_response(problem: ProblemDetail) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(ServiceOSException)
    async def serviceos_exception_handler(request: Request, exc: ServiceOSException) -> JSONResponse:
        problem = make_problem(
            error_code=exc.error_code,
            detail=exc.detail,
            instance=str(request.url.path),
            blocking_rule=exc.blocking_rule,
            resolution=exc.resolution,
            request_id=_get_request_id(request),
            context=exc.context,
        )
        if exc.status_code:
            problem.status = exc.status_code
        logger.warning(
            "serviceos.exception",
            error_code=exc.error_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return _problem_response(problem)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        error_map = {
            401: "UNAUTHORIZED",
            403: "PERMISSION_DENIED",
            404: "NOT_FOUND",
            409: "CONFLICT",
            429: "RATE_LIMITED",
        }
        error_code = error_map.get(exc.status_code, "INTERNAL_ERROR")
        problem = make_problem(
            error_code=error_code,
            detail=str(exc.detail),
            instance=str(request.url.path),
            request_id=_get_request_id(request),
        )
        problem.status = exc.status_code
        return _problem_response(problem)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            ValidationErrorItem(
                field=".".join(str(loc) for loc in e["loc"]),
                message=e["msg"],
                received=e.get("input"),
            )
            for e in exc.errors()
        ]
        problem = ValidationProblemDetail(
            type="https://serviceos.io/errors/VALIDATION_ERROR",
            title="Validation Error",
            status=422,
            detail="One or more request fields failed validation.",
            instance=str(request.url.path),
            error_code="VALIDATION_ERROR",
            resolution="Check the 'errors' array for field-level details.",
            request_id=_get_request_id(request),
            errors=errors,
        )
        logger.info("validation.error", path=request.url.path, error_count=len(errors))
        return _problem_response(problem)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.error(
            "unhandled.exception",
            error=str(exc),
            path=request.url.path,
            request_id=request_id,
            traceback=traceback.format_exc(),
        )
        problem = make_problem(
            error_code="INTERNAL_ERROR",
            detail="An unexpected error occurred. Our team has been notified.",
            instance=str(request.url.path),
            request_id=request_id,
            resolution="If this persists, contact support with the request_id.",
            context={"request_id": request_id} if not False else None,  # never leak internals in prod
        )
        return _problem_response(problem)
