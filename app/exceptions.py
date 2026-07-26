"""
ServiceOS — Global Exception Handlers
All unhandled exceptions are converted to RFC 7807 Problem Details.
No raw Python exceptions ever reach the client.
"""
import re
import traceback
import uuid
from typing import Any

# A bare ValueError whose message is a domain error *code* — ALL_CAPS_SNAKE, no
# spaces, e.g. "COMPLAINT_ACCESS_DENIED" — is the codebase's idiom for a domain
# rejection raised from a service layer (raise ValueError(ERR_CONSTANT)). These
# should surface as a 4xx to the client, not a 500. Genuine Python ValueErrors
# ("invalid literal for int()", etc.) contain spaces/lowercase and fall through
# to the 500 handler unchanged.
_DOMAIN_CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")


def _domain_code_status(code: str) -> int | None:
    """Map a domain error code to a 4xx status, or None if it is not code-like.

    Also accepts the `CODE: human detail` form some services raise
    (e.g. "COMPLAINT_INVALID_STATUS_TRANSITION: open -> resolution_proposed") by
    inspecting only the leading token before the first colon."""
    if not code:
        return None
    head = code.split(":", 1)[0].strip()
    if len(head) > 80 or not _DOMAIN_CODE_RE.match(head):
        return None
    code = head
    if "NOT_FOUND" in code or code.endswith("_MISSING"):
        return 404
    if "ACCESS_DENIED" in code or "DENIED" in code or "FORBIDDEN" in code or "NOT_ALLOWED" in code:
        return 403
    if "UNAUTHORIZED" in code:
        return 401
    if "CONFLICT" in code or "ALREADY" in code or "DUPLICATE" in code:
        return 409
    return 422

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


class VerticalDisabledException(ServiceOSException):
    def __init__(self, vertical_key: str):
        super().__init__(
            error_code="VERTICAL_DISABLED",
            detail=f"This business vertical ('{vertical_key}') is currently unavailable.",
            status_code=403,
            blocking_rule=f"verticals.{vertical_key}.is_enabled must be true",
            resolution="Contact your platform admin, or try again later.",
            context={"vertical_key": vertical_key},
        )


class TenantVerticalNotActiveException(ServiceOSException):
    def __init__(self, vertical_key: str, tenant_id: str, enrollment_status: str | None = None):
        super().__init__(
            error_code="TENANT_VERTICAL_NOT_ACTIVE",
            detail=f"Tenant '{tenant_id}' does not have an active enrollment in '{vertical_key}'.",
            status_code=403,
            blocking_rule="tenant_vertical_enrollments.status must be 'active'",
            resolution="Ask your platform admin to approve/activate this vertical for your account.",
            context={"vertical_key": vertical_key, "tenant_id": tenant_id, "enrollment_status": enrollment_status},
        )


class VerticalCapabilityUnavailableException(ServiceOSException):
    def __init__(self, vertical_key: str, capability: str):
        super().__init__(
            error_code="VERTICAL_CAPABILITY_UNAVAILABLE",
            detail=f"Capability '{capability}' is not enabled for vertical '{vertical_key}'.",
            status_code=403,
            blocking_rule=f"'{capability}' not in verticals.{vertical_key}.capabilities",
            resolution="Contact your platform admin to enable this capability for this vertical.",
            context={"vertical_key": vertical_key, "capability": capability},
        )


class CrossVerticalAccessException(ServiceOSException):
    def __init__(self, resource: str, resource_id: str, expected_vertical: str):
        super().__init__(
            error_code="CROSS_VERTICAL_ACCESS_DENIED",
            detail=f"{resource} '{resource_id}' does not belong to vertical '{expected_vertical}'.",
            status_code=403,
            resolution="Verify the resource ID and the vertical context of your request.",
            context={"resource": resource, "resource_id": resource_id, "expected_vertical": expected_vertical},
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
        elif problem.status == 500:
            # The code wasn't in ERROR_CODES so make_problem defaulted to 500.
            # A domain-code-shaped error (e.g. DUPLICATE_OPEN_REQUEST, INVALID_STATE)
            # is a client error, not a server fault — infer its 4xx from the code
            # so unregistered codes don't leak as 500s. Only downgrades 500→4xx.
            inferred = _domain_code_status(exc.error_code)
            if inferred is not None:
                problem.status = inferred
        logger.warning(
            "serviceos.exception",
            error_code=exc.error_code,
            detail=exc.detail,
            path=request.url.path,
            status=problem.status,
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

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        # MODULE-L5-02 bug #24: service layers across the app raise bare
        # ValueError(ERR_CODE) for domain rejections (not found / access denied /
        # already-exists / invalid state). Handlers that forgot to catch them let
        # them hit the catch-all below as 500s — a recurring class of false
        # "Internal Server Error"s on legitimate 4xx conditions (complaints,
        # invoices, reviews, ...). Map code-like ValueErrors to the right 4xx;
        # anything that is not a domain code still falls through to a 500.
        raw = str(exc)
        st = _domain_code_status(raw)
        if st is None:
            return await unhandled_exception_handler(request, exc)
        # Use only the clean leading code token as the client-facing error_code
        # (the full message may carry a human detail after a colon, including
        # non-ASCII like "->" that must not leak into the code/detail fields).
        code = raw.split(":", 1)[0].strip()
        detail = raw.split(":", 1)[1].strip() if ":" in raw else code.replace("_", " ").title()
        problem = make_problem(
            error_code=code,
            detail=detail,
            instance=str(request.url.path),
            request_id=_get_request_id(request),
        )
        problem.status = st
        logger.info("domain.value_error", error_code=code, status=st, path=request.url.path)
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
