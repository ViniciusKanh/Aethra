from ..config import Settings
from ..models import ChatRequest, TextTaskResponse
from ..providers import BaseProvider


class ChatService:
    """Orquestra requisicoes de chat sem depender da engine configurada."""

    def __init__(self, provider: BaseProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    def executar(self, payload: ChatRequest) -> TextTaskResponse:
        model = payload.model or self.settings.default_chat_model
        messages: list[dict[str, str]] = []
        if payload.system_prompt:
            messages.append({"role": "system", "content": payload.system_prompt})
        messages.append({"role": "user", "content": payload.pergunta})

        resultado = self.provider.chat_completion(
            model=model,
            messages=messages,
            temperature=payload.temperatura,
            max_tokens=payload.max_tokens,
        )
        return TextTaskResponse(
            status="ok",
            model=resultado.model,
            resposta=resultado.resposta,
            metadados=resultado.metadados,
        )
