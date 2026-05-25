from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .providers import ProviderError, create_provider
from .routes import chat_router, health_router, summarize_router, vision_router
from .services import ChatService, SummarizeService, VisionService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Monta a aplicacao e injeta o provider configurado nos servicos."""

    active_settings = settings or get_settings()
    provider = create_provider(active_settings)
    app = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        description=active_settings.app_description,
        docs_url="/docs" if active_settings.enable_docs else None,
        redoc_url="/redoc" if active_settings.enable_docs else None,
        openapi_url="/openapi.json" if active_settings.enable_docs else None,
    )

    # CORS atende clientes de navegador; integracoes servidor-a-servidor nao dependem dele.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    app.state.settings = active_settings
    app.state.provider = provider
    app.state.chat_service = ChatService(provider, active_settings)
    app.state.summarize_service = SummarizeService(provider, active_settings)
    app.state.vision_service = VisionService(provider, active_settings)

    @app.exception_handler(ProviderError)
    async def provider_error_handler(_: Request, exc: ProviderError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(summarize_router)
    app.include_router(vision_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8080, reload=True)
