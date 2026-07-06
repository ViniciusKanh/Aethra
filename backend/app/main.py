from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .providers import ProviderError, create_provider
from .routes import (
    admin_router,
    auth_router,
    chat_router,
    conversations_router,
    health_router,
    knowledge_router,
    summarize_router,
    vision_router,
)
from .services import (
    AssistantService,
    AuthError,
    ChatService,
    ConversationService,
    KnowledgeError,
    KnowledgeService,
    RuntimeConfigError,
    RuntimeConfigService,
    SummarizeService,
    TursoError,
    TursoService,
    UserService,
    VisionService,
)


def create_app(
    settings: Settings | None = None,
    turso_service: TursoService | None = None,
) -> FastAPI:
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "ngrok-skip-browser-warning"],
    )

    app.state.settings = active_settings
    app.state.provider = provider
    app.state.runtime_config_service = RuntimeConfigService(active_settings)
    app.state.runtime_config_service.initialize()
    app.state.turso_service = turso_service or TursoService(
        app.state.runtime_config_service,
        timeout=min(active_settings.request_timeout, 60),
    )
    app.state.storage_startup_error = None
    app.state.user_service = UserService(active_settings, app.state.turso_service)
    try:
        app.state.user_service.initialize()
    except TursoError as exc:
        app.state.storage_startup_error = exc.detail

    app.state.chat_service = ChatService(provider, active_settings)
    app.state.summarize_service = SummarizeService(provider, active_settings)
    app.state.vision_service = VisionService(provider, active_settings)
    app.state.knowledge_service = KnowledgeService(
        provider,
        active_settings,
        app.state.runtime_config_service,
    )
    app.state.conversation_service = ConversationService(app.state.turso_service)
    app.state.assistant_service = AssistantService(
        app.state.knowledge_service,
        app.state.conversation_service,
    )

    for error_type in (ProviderError, KnowledgeError, AuthError, RuntimeConfigError, TursoError):
        app.add_exception_handler(
            error_type,
            lambda _request, exc: JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}),
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(conversations_router)
    app.include_router(summarize_router)
    app.include_router(vision_router)
    app.include_router(knowledge_router)
    app.include_router(admin_router)

    frontend_dir = active_settings.resolved_frontend_dir
    if active_settings.frontend_enabled and frontend_dir.exists():
        app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="aethra-frontend")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8081, reload=True)
