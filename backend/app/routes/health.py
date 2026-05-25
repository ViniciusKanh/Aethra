from fastapi import APIRouter, Request

from ..models import HealthResponse, RootResponse

router = APIRouter()


@router.get("/", response_model=RootResponse, tags=["Base"])
def raiz(request: Request) -> RootResponse:
    return RootResponse(
        mensagem="API da Aethra online.",
        docs="/docs" if request.app.state.settings.enable_docs else "disabled",
        status="ok",
    )


@router.get("/health", response_model=HealthResponse, tags=["Monitoramento"])
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    provider = request.app.state.provider
    provider_ok = provider.health_check()
    provider_status = "online" if provider_ok else "offline"
    return HealthResponse(
        status="ok" if provider_ok else "degraded",
        api="online",
        provider=provider.name,
        provider_status=provider_status,
        default_chat_model=settings.default_chat_model,
        default_vision_model=settings.default_vision_model,
        # Campo legado para clientes antigos que consultavam o status do Ollama.
        ollama=provider_status,
    )
