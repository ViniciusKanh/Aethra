from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator


class RootResponse(BaseModel):
    mensagem: str
    docs: str
    status: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    role: Literal["admin", "user"]
    is_active: bool
    created_at: str


class AuthStatusResponse(BaseModel):
    enabled: bool
    registration_enabled: bool
    storage_configured: bool
    storage_online: bool
    requires_setup: bool
    admin_email: EmailStr | None
    company_name: str


class SetupAdminRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=12, max_length=128)
    turso_database_url: str | None = Field(default=None, max_length=500)
    turso_auth_token: str | None = Field(default=None, max_length=4_000)


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserResponse


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)


class UserAdminUpdate(BaseModel):
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None


class HealthResponse(BaseModel):
    status: str
    api: str
    provider: str
    provider_status: str
    auth_enabled: bool
    default_chat_model: str
    default_vision_model: str
    ollama: str = Field(description="Campo legado que reflete o provider ativo.")


class TursoConfigUpdate(BaseModel):
    database_url: str = Field(..., min_length=12, max_length=500)
    auth_token: str | None = Field(default=None, max_length=4_000)


class AdminConfigResponse(BaseModel):
    environment: str
    provider: str
    chat_model: str
    embedding_model: str
    request_timeout: int
    company_name: str
    registration_enabled: bool
    turso_database_url: str | None
    turso_token_configured: bool
    turso_online: bool
    knowledge_enabled: bool
    knowledge_folder_id: str | None
    knowledge_credentials_configured: bool
    knowledge_service_account_email: str | None
    knowledge_embedding_model: str
    knowledge_top_k: int
    knowledge_chunk_size: int
    knowledge_chunk_overlap: int


class KnowledgeConfigUpdate(BaseModel):
    enabled: bool = True
    folder_id: str = Field(..., min_length=5, max_length=255)
    service_account_json: str | None = Field(default=None, max_length=20_000)
    embedding_model: str = Field(default="qwen3-embedding:0.6b", min_length=2, max_length=200)
    top_k: int = Field(default=6, ge=2, le=20)
    chunk_size: int = Field(default=1_200, ge=300, le=4_000)
    chunk_overlap: int = Field(default=180, ge=0, le=1_000)

    @model_validator(mode="after")
    def validar_chunking(self) -> "KnowledgeConfigUpdate":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap deve ser menor que chunk_size.")
        return self


class KnowledgeStatusResponse(BaseModel):
    status: Literal["pending", "indexing", "ready", "error"]
    enabled: bool = False
    configured: bool = False
    folder_id: str | None = None
    service_account_email: str | None = None
    embedding_model: str | None = None
    last_sync_at: str | None = None
    document_count: int = 0
    page_count: int = 0
    chunk_count: int = 0
    error: str | None = None


class KnowledgeSyncResponse(KnowledgeStatusResponse):
    files: list[str] = Field(default_factory=list)


class KnowledgeCitation(BaseModel):
    index: int
    file_id: str
    file_name: str
    file_type: str
    location: str
    page: int | None = None
    excerpt: str
    web_url: str


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8_000)


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class StoredMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    citations: list[KnowledgeCitation] = Field(default_factory=list)
    created_at: str


class ConversationDetail(ConversationSummary):
    messages: list[StoredMessage] = Field(default_factory=list)


class EnterpriseChatRequest(BaseModel):
    pergunta: str = Field(..., min_length=1, max_length=2_000)
    conversation_id: str | None = Field(default=None, max_length=100)
    historico: list[ConversationMessage] = Field(default_factory=list, max_length=12)
    model: str | None = None
    temperatura: float = Field(default=0.1, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=1_200, gt=0, le=4_000)


class EnterpriseChatResponse(BaseModel):
    status: str
    model: str
    resposta: str
    conversation_id: str
    used_knowledge: bool = True
    citations: list[KnowledgeCitation] = Field(default_factory=list)
    metadados: dict[str, Any]


class ChatRequest(BaseModel):
    pergunta: str = Field(..., min_length=1, description="Pergunta enviada pelo usuario")
    system_prompt: str | None = Field(
        default="Voce e um assistente tecnico, objetivo e util. Responda em portugues do Brasil.",
    )
    model: str | None = None
    temperatura: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


class SummarizeRequest(BaseModel):
    texto: str = Field(..., min_length=1)
    instrucoes: str | None = "Resuma o texto de forma objetiva, preservando os pontos principais."
    model: str | None = None
    max_tokens: int | None = Field(default=None, gt=0)


class EmailSummarizeRequest(BaseModel):
    assunto: str | None = None
    remetente: str | None = None
    corpo: str = Field(..., min_length=1, validation_alias=AliasChoices("corpo", "texto", "body"))
    instrucoes: str | None = Field(
        default="Resuma este e-mail, identifique o problema principal, a prioridade e a proxima acao recomendada.",
        validation_alias=AliasChoices("instrucoes", "objetivo", "instructions"),
    )
    model: str | None = None
    max_tokens: int | None = Field(default=700, gt=0)
    model_config = ConfigDict(populate_by_name=True)


class VisionRequest(BaseModel):
    imagem_base64: str
    prompt: str | None = "Descreva a imagem e interprete seus elementos principais em portugues do Brasil."
    model: str | None = None
    imagem_media_type: str = "image/jpeg"
    max_tokens: int | None = Field(default=None, gt=0)


class TextTaskResponse(BaseModel):
    status: str
    model: str
    resposta: str
    metadados: dict[str, Any]
