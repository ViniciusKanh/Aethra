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
        if frontend_path.is_absolute():
            return frontend_path
        return Path.cwd() / frontend_path

    @model_validator(mode="after")
    def validar_seguranca_producao(self) -> "Settings":
        """Impede inicializacao em producao com protecoes essenciais ausentes."""

        if self.environment == "production":
            if self.auth_enabled and (not self.api_key or len(self.api_key) < 32):
                raise ValueError("Com AUTH_ENABLED=true, API_KEY deve conter pelo menos 32 caracteres.")
            if "*" in self.allowed_origins:
                raise ValueError("Em producao, CORS_ORIGINS nao pode permitir qualquer origem.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna uma unica instancia de configuracao para a aplicacao."""

    return Settings()
