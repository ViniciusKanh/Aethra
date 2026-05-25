from ..config import Settings
from .base import BaseProvider
from .ollama_provider import OllamaProvider
from .vllm_provider import VLLMProvider


def create_provider(settings: Settings) -> BaseProvider:
    """Instancia o provider ativo sem expor detalhes para as rotas."""

    if settings.provider == "vllm":
        return VLLMProvider(
            base_url=settings.vllm_base_url,
            api_key=settings.vllm_api_key,
            timeout=settings.request_timeout,
        )
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        timeout=settings.request_timeout,
    )
