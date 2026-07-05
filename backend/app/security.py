import secrets

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def require_api_key(
    request: Request,
    provided_api_key: str | None = Security(api_key_header),
) -> None:
    """Valida o consumidor da API quando uma chave foi configurada."""

    settings = request.app.state.settings
    if not settings.auth_enabled:
        return

    configured_api_key = settings.api_key
    if not configured_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autenticacao da API esta ativa, mas a chave nao foi configurada.",
        )

    if not provided_api_key or not secrets.compare_digest(provided_api_key, configured_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key ausente ou invalida.",
        )


def require_admin_key(
    request: Request,
    provided_admin_key: str | None = Security(admin_key_header),
) -> None:
    """Protege configuracoes e dados corporativos com uma chave exclusiva."""

    settings = request.app.state.settings
    if not settings.admin_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso nao encontrado.")

    configured_admin_key = settings.admin_api_key
    if not configured_admin_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Console administrativo sem chave configurada.",
        )
    if not provided_admin_key or not secrets.compare_digest(provided_admin_key, configured_admin_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial administrativa ausente ou invalida.",
        )
