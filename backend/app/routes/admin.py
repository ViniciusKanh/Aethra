from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from ..models import AdminConfigResponse, DwSchemaResponse
from ..security import require_admin_key

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin_key)])


@router.get("/config", response_model=AdminConfigResponse, tags=["Administracao"])
def admin_config(request: Request) -> AdminConfigResponse:
    settings = request.app.state.settings
    return AdminConfigResponse(
        environment=settings.environment,
        provider=settings.provider,
        chat_model=settings.default_chat_model,
        vision_model=settings.default_vision_model,
        request_timeout=settings.request_timeout,
        auth_enabled=settings.auth_enabled,
        admin_enabled=settings.admin_enabled,
        dw_enabled=settings.dw_enabled,
        dw_host=settings.dw_host if settings.dw_enabled else None,
        dw_port=settings.dw_port if settings.dw_enabled else None,
        dw_database=settings.dw_database if settings.dw_enabled else None,
        dw_user=settings.dw_user if settings.dw_enabled else None,
        dw_password_configured=bool(settings.dw_password),
        dw_sslmode=settings.dw_sslmode if settings.dw_enabled else None,
        dw_allowed_schemas=settings.allowed_dw_schemas,
        dw_table_prefixes=settings.allowed_dw_table_prefixes,
        dw_statement_timeout_ms=settings.dw_statement_timeout_ms,
        dw_max_rows=settings.dw_max_rows,
    )


@router.post("/dw/test", response_model=dict[str, Any], tags=["Administracao"])
def admin_dw_test(request: Request) -> dict[str, Any]:
    return request.app.state.warehouse_service.admin_status()


@router.get("/dw/schema", response_model=DwSchemaResponse, tags=["Administracao"])
def admin_dw_schema(
    request: Request,
    refresh: bool = Query(default=False),
) -> DwSchemaResponse:
    return request.app.state.warehouse_service.get_schema(force_refresh=refresh)
