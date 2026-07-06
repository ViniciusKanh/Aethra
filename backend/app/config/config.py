from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracoes da API e dos providers carregadas do ambiente."""

    environment: Literal["development", "production"] = Field(
        default="development",
        alias="ENVIRONMENT",
    )
    auth_enabled: bool = Field(default=False, alias="AUTH_ENABLED")
    api_key: str | None = Field(default=None, alias="API_KEY")
    cors_origins: str = Field(default="http://localhost:5500", alias="CORS_ORIGINS")
    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")
    frontend_enabled: bool = Field(default=True, alias="FRONTEND_ENABLED")
    frontend_dir: str = Field(default="frontend", alias="FRONTEND_DIR")

    user_auth_enabled: bool = Field(default=True, alias="USER_AUTH_ENABLED")
    registration_enabled: bool = Field(default=True, alias="REGISTRATION_ENABLED")
    admin_email: str = Field(default="", alias="ADMIN_EMAIL")
    local_config_db_path: str = Field(default="backend/data/aethra_config.db", alias="LOCAL_CONFIG_DB_PATH")
    config_key_path: str = Field(default="backend/data/.config_key", alias="CONFIG_KEY_PATH")
    company_name: str = Field(default="Aethra", alias="COMPANY_NAME")
    session_ttl_hours: int = Field(default=12, ge=1, le=720, alias="SESSION_TTL_HOURS")
    max_login_attempts: int = Field(default=5, ge=3, le=20, alias="MAX_LOGIN_ATTEMPTS")
    login_lock_minutes: int = Field(default=15, ge=1, le=1_440, alias="LOGIN_LOCK_MINUTES")
    bootstrap_admin_email: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_password: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_PASSWORD")

    turso_database_url: str = Field(default="", alias="TURSO_DATABASE_URL")
    turso_auth_token: str = Field(default="", alias="TURSO_AUTH_TOKEN")

    provider: Literal["vllm", "ollama"] = Field(default="vllm", alias="PROVIDER")

    vllm_base_url: str = Field(default="http://localhost:8000/v1", alias="VLLM_BASE_URL")
    vllm_api_key: str = Field(default="EMPTY", alias="VLLM_API_KEY")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    default_chat_model: str = Field(
        default="meta-llama/Llama-4-Scout-17B-16E-Instruct",
        alias="DEFAULT_CHAT_MODEL",
    )
    default_vision_model: str = Field(
        default="meta-llama/Llama-4-Scout-17B-16E-Instruct",
        alias="DEFAULT_VISION_MODEL",
    )
    request_timeout: int = Field(default=300, ge=1, alias="REQUEST_TIMEOUT")

    knowledge_index_path: str = Field(default="backend/data/knowledge", alias="KNOWLEDGE_INDEX_PATH")
    default_embedding_model: str = Field(
        default="qwen3-embedding:0.6b",
        alias="DEFAULT_EMBEDDING_MODEL",
    )
    google_drive_max_file_mb: int = Field(default=50, ge=1, le=500, alias="GOOGLE_DRIVE_MAX_FILE_MB")

    app_name: str = Field(default="Aethra API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    app_description: str = Field(
        default="API da Aethra para chat, resumo e visao",
        alias="APP_DESCRIPTION",
    )

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def allowed_origins(self) -> list[str]:
        """Converte a lista de origens separada por virgula para o CORS."""

        return [origem.strip() for origem in self.cors_origins.split(",") if origem.strip()]

    @property
    def resolved_frontend_dir(self) -> Path:
        """Resolve o diretorio do frontend a partir da raiz do projeto."""

        frontend_path = Path(self.frontend_dir)
        resolved = frontend_path if frontend_path.is_absolute() else Path.cwd() / frontend_path
        vite_dist = resolved / "dist"
        if (vite_dist / "index.html").exists():
            return vite_dist
        return resolved

    def resolve_local_path(self, configured_path: str) -> Path:
        """Resolve caminhos de persistencia local sem depender do shell atual."""

        path = Path(configured_path)
        return path if path.is_absolute() else Path.cwd() / path

    @property
    def resolved_local_config_db_path(self) -> Path:
        """Resolve o SQLite local usado somente para configuracoes criptografadas."""

        db_path = Path(self.local_config_db_path)
        if db_path.is_absolute():
            return db_path
        return Path.cwd() / db_path

    @property
    def resolved_knowledge_index_path(self) -> Path:
        """Resolve o diretorio persistente do indice vetorial local."""

        return self.resolve_local_path(self.knowledge_index_path)

    @model_validator(mode="after")
    def validar_seguranca_producao(self) -> "Settings":
        """Impede inicializacao em producao com protecoes essenciais ausentes."""

        if self.environment == "production":
            if self.auth_enabled and (not self.api_key or len(self.api_key) < 32):
                raise ValueError("Com AUTH_ENABLED=true, API_KEY deve conter pelo menos 32 caracteres.")
            if "*" in self.allowed_origins:
                raise ValueError("Em producao, CORS_ORIGINS nao pode permitir qualquer origem.")
        bootstrap_values = (self.bootstrap_admin_email, self.bootstrap_admin_password)
        if any(bootstrap_values) and not all(bootstrap_values):
            raise ValueError("BOOTSTRAP_ADMIN_EMAIL e BOOTSTRAP_ADMIN_PASSWORD devem ser definidos juntos.")
        if self.bootstrap_admin_password and len(self.bootstrap_admin_password) < 12:
            raise ValueError("BOOTSTRAP_ADMIN_PASSWORD deve conter pelo menos 12 caracteres.")
        if bool(self.turso_database_url) != bool(self.turso_auth_token):
            raise ValueError("TURSO_DATABASE_URL e TURSO_AUTH_TOKEN devem ser definidos juntos.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna uma unica instancia de configuracao para a aplicacao."""

    return Settings()
