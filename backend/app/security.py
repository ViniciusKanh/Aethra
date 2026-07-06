import secrets

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from .models import UserResponse

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def _valid_api_key(request: Request, provided_api_key: str | None) -> bool:
    settings = request.app.state.settings
    if not settings.auth_enabled:
        return False
    configured = settings.api_key
    return bool(configured and provided_api_key and secrets.compare_digest(provided_api_key, configured))


def require_api_key(
    request: Request,
    provided_api_key: str | None = Security(api_key_header),
) -> None:
    """Mantem compatibilidade para integracoes servidor-a-servidor."""

    settings = request.app.state.settings
    if not settings.auth_enabled:
        return
    if not settings.api_key:
        raise HTTPException(status_code=503, detail="Autenticacao da API sem chave configurada.")
    if not _valid_api_key(request, provided_api_key):
        raise HTTPException(status_code=401, detail="API key ausente ou invalida.")


def require_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> UserResponse:
    """Valida uma sessao opaca e revogavel emitida no login."""

    if not request.app.state.settings.user_auth_enabled:
        raise HTTPException(status_code=404, detail="Autenticacao de usuarios desativada.")
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faca login para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return request.app.state.user_service.authenticate(credentials.credentials)


def require_admin_user(user: UserResponse = Security(require_authenticated_user)) -> UserResponse:
    """Autoriza apenas administradores ativos."""

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo para administradores.")
    return user


def require_user_or_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    provided_api_key: str | None = Security(api_key_header),
) -> UserResponse | None:
    """Aceita sessao de usuario no front ou API key em integracoes tecnicas."""

    settings = request.app.state.settings
    if settings.user_auth_enabled:
        if credentials and credentials.scheme.lower() == "bearer":
            return request.app.state.user_service.authenticate(credentials.credentials)
        if _valid_api_key(request, provided_api_key):
            return None
        raise HTTPException(
            status_code=401,
            detail="Faca login ou envie uma API key valida.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    require_api_key(request, provided_api_key)
    return None
