from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RootResponse(BaseModel):
    mensagem: str
    docs: str
    status: str


class HealthResponse(BaseModel):
    status: str
    api: str
    provider: str
    provider_status: str
    auth_enabled: bool
    default_chat_model: str
    default_vision_model: str
    ollama: str = Field(
        description="Campo legado mantido por compatibilidade; reflete o status do provider ativo."
    )


class ChatRequest(BaseModel):
    pergunta: str = Field(..., min_length=1, description="Pergunta enviada pelo usuario")
    system_prompt: str | None = Field(
        default="Voce e um assistente tecnico, objetivo e util. Responda em portugues do Brasil.",
        description="Prompt de sistema opcional",
    )
    model: str | None = Field(default=None, description="Modelo servido pelo provider ativo")
    temperatura: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


class SummarizeRequest(BaseModel):
    texto: str = Field(..., min_length=1, description="Texto a ser resumido")
    instrucoes: str | None = Field(
        default="Resuma o texto de forma objetiva, preservando os pontos principais.",
        description="Instrucoes adicionais para o resumo",
    )
    model: str | None = Field(default=None, description="Modelo servido pelo provider ativo")
    max_tokens: int | None = Field(default=None, gt=0)


class EmailSummarizeRequest(BaseModel):
    """Entrada facilitada para resumir e-mails recebidos por API ou pelo frontend."""

    assunto: str | None = Field(default=None, description="Assunto do e-mail, quando disponivel")
    remetente: str | None = Field(default=None, description="Remetente do e-mail, quando disponivel")
    corpo: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("corpo", "texto", "body"),
        description="Corpo do e-mail. Tambem aceita os aliases texto ou body.",
    )
    instrucoes: str | None = Field(
        default=(
            "Resuma este e-mail, identifique o problema principal, "
            "a prioridade e a proxima acao recomendada."
        ),
        validation_alias=AliasChoices("instrucoes", "objetivo", "instructions"),
        description="Instrucoes opcionais para guiar a analise do e-mail",
    )
    model: str | None = Field(default=None, description="Modelo servido pelo provider ativo")
    max_tokens: int | None = Field(default=700, gt=0)

    model_config = ConfigDict(populate_by_name=True)


class VisionRequest(BaseModel):
    imagem_base64: str = Field(..., description="Imagem em base64 sem prefixo data:image")
    prompt: str | None = Field(
        default="Descreva a imagem e interprete seus elementos principais em portugues do Brasil.",
        description="Prompt da analise visual",
    )
    model: str | None = Field(default=None, description="Modelo multimodal servido pelo provider ativo")
    imagem_media_type: str = Field(default="image/jpeg", description="MIME type da imagem recebida")
    max_tokens: int | None = Field(default=None, gt=0)


class TextTaskResponse(BaseModel):
    status: str
    model: str
    resposta: str
    metadados: dict[str, Any]
