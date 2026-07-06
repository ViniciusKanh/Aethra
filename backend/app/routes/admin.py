from typing import Any

from fastapi import APIRouter, Depends, Request

from ..models import (
    AdminConfigResponse,
    KnowledgeConfigUpdate,
    KnowledgeStatusResponse,
    KnowledgeSyncResponse,
    TursoConfigUpdate,
    UserAdminUpdate,
    UserResponse,
)
from ..security import require_admin_user

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin_user)])


def _config_response(request: Request) -> AdminConfigResponse:
    settings = request.app.state.settings
    turso = request.app.state.runtime_config_service.get_turso_config()
    knowledge = request.app.state.runtime_config_service.get_knowledge_config()
    return AdminConfigResponse(
        environment=settings.environment,
        provider=settings.provider,
        chat_model=settings.default_chat_model,
        embedding_model=settings.default_embedding_model,
        request_timeout=settings.request_timeout,
        company_name=settings.company_name,
        registration_enabled=settings.registration_enabled,
        turso_database_url=turso.database_url or None,
        turso_token_configured=bool(turso.auth_token),
        turso_online=turso.configured and not bool(request.app.state.storage_startup_error),
        knowledge_enabled=knowledge.enabled,
        knowledge_folder_id=knowledge.folder_id or None,
        knowledge_credentials_configured=bool(knowledge.service_account_json),
        knowledge_service_account_email=knowledge.service_account_email,
        knowledge_embedding_model=knowledge.embedding_model,
        knowledge_top_k=knowledge.top_k,
        knowledge_chunk_size=knowledge.chunk_size,
        knowledge_chunk_overlap=knowledge.chunk_overlap,
    )


@router.get("/config", response_model=AdminConfigResponse, tags=["Administracao"])
def admin_config(request: Request) -> AdminConfigResponse:
    return _config_response(request)


@router.put("/turso/config", response_model=AdminConfigResponse, tags=["Administracao"])
def save_turso_config(
    payload: TursoConfigUpdate,
    request: Request,
    admin: UserResponse = Depends(require_admin_user),
) -> AdminConfigResponse:
    request.app.state.runtime_config_service.save_turso_config(payload, admin.id)
    request.app.state.turso_service.initialize()
    request.app.state.storage_startup_error = None
    return _config_response(request)


@router.post("/turso/test", response_model=dict[str, Any], tags=["Administracao"])
def test_turso(request: Request) -> dict[str, Any]:
    return request.app.state.turso_service.test_connection()


@router.put("/knowledge/config", response_model=AdminConfigResponse, tags=["Administracao"])
def save_knowledge_config(
    payload: KnowledgeConfigUpdate,
    request: Request,
    admin: UserResponse = Depends(require_admin_user),
) -> AdminConfigResponse:
    request.app.state.runtime_config_service.save_knowledge_config(payload, admin.id)
    return _config_response(request)


@router.post("/knowledge/test", response_model=dict[str, Any], tags=["Administracao"])
def admin_knowledge_test(request: Request) -> dict[str, Any]:
    return request.app.state.knowledge_service.test_connection()


@router.post("/knowledge/sync", response_model=KnowledgeSyncResponse, tags=["Administracao"])
def admin_knowledge_sync(
    request: Request,
    admin: UserResponse = Depends(require_admin_user),
) -> KnowledgeSyncResponse:
    return request.app.state.knowledge_service.sync(admin.id)


@router.get("/knowledge/status", response_model=KnowledgeStatusResponse, tags=["Administracao"])
def admin_knowledge_status(request: Request) -> KnowledgeStatusResponse:
    return request.app.state.knowledge_service.status()


@router.get("/users", response_model=list[UserResponse], tags=["Administracao"])
def list_users(request: Request) -> list[UserResponse]:
    return request.app.state.user_service.list_users()


@router.patch("/users/{user_id}", response_model=UserResponse, tags=["Administracao"])
def update_user(
    user_id: str,
    payload: UserAdminUpdate,
    request: Request,
    admin: UserResponse = Depends(require_admin_user),
) -> UserResponse:
    return request.app.state.user_service.update_user(admin.id, user_id, payload)
