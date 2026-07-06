from fastapi import APIRouter, Depends, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials

from ..models import (
    AuthResponse,
    AuthStatusResponse,
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    SetupAdminRequest,
    TursoConfigUpdate,
    UserResponse,
)
from ..security import bearer_scheme, require_authenticated_user

router = APIRouter(prefix="/auth", tags=["Autenticacao"])


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(request: Request) -> AuthStatusResponse:
    settings = request.app.state.settings
    storage_configured = request.app.state.turso_service.configured
    storage_online = storage_configured and not bool(request.app.state.storage_startup_error)
    return AuthStatusResponse(
        enabled=settings.user_auth_enabled,
        registration_enabled=settings.registration_enabled and settings.user_auth_enabled,
        storage_configured=storage_configured,
        storage_online=storage_online,
        requires_setup=not storage_online or request.app.state.user_service.count_users() == 0,
        admin_email=settings.admin_email or None,
        company_name=settings.company_name,
    )


@router.post("/setup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def setup_admin(payload: SetupAdminRequest, request: Request) -> AuthResponse:
    if not request.app.state.settings.user_auth_enabled:
        from ..services import AuthError

        raise AuthError(404, "Autenticacao de usuarios esta desativada.")
    if payload.turso_database_url or payload.turso_auth_token:
        request.app.state.runtime_config_service.save_turso_config(
            TursoConfigUpdate(
                database_url=payload.turso_database_url or "",
                auth_token=payload.turso_auth_token,
            )
        )
        request.app.state.turso_service.initialize()
        request.app.state.storage_startup_error = None
    elif not request.app.state.turso_service.configured or request.app.state.storage_startup_error:
        from ..services import AuthError

        raise AuthError(422, "Informe uma URL e um novo token Turso validos.")
    client_host = request.client.host if request.client else ""
    return request.app.state.user_service.setup_admin(payload, client_host)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request) -> AuthResponse:
    if not request.app.state.settings.user_auth_enabled:
        from ..services import AuthError

        raise AuthError(404, "Autenticacao de usuarios esta desativada.")
    return request.app.state.user_service.register(payload)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request) -> AuthResponse:
    if not request.app.state.settings.user_auth_enabled:
        from ..services import AuthError

        raise AuthError(404, "Autenticacao de usuarios esta desativada.")
    return request.app.state.user_service.login(payload)


@router.get("/me", response_model=UserResponse)
def me(user: UserResponse = Depends(require_authenticated_user)) -> UserResponse:
    return user


@router.post("/password", response_model=AuthResponse)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    user: UserResponse = Depends(require_authenticated_user),
) -> AuthResponse:
    return request.app.state.user_service.change_password(user.id, payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    _: UserResponse = Depends(require_authenticated_user),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    if credentials:
        request.app.state.user_service.logout(credentials.credentials)
