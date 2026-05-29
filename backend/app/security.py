import secrets

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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
        return

    if not provided_api_key or not secrets.compare_digest(provided_api_key, configured_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key ausente ou invalida.",
        )
