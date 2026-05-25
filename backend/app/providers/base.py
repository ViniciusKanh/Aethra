from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


Message = dict[str, Any]


@dataclass(frozen=True)
class CompletionResult:
    """Resposta normalizada para que as rotas nao dependam da engine."""

    model: str
    resposta: str
    metadados: dict[str, Any]


class ProviderError(Exception):
    """Erro controlado durante comunicacao com um provider de inferencia."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class BaseProvider(ABC):
    """Contrato minimo implementado por engines de serving suportadas."""

    name: str

    @abstractmethod
    def health_check(self) -> bool:
        """Informa se o provider pode receber requisicoes."""

    @abstractmethod
    def chat_completion(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        """Executa uma completion usando mensagens no formato de chat."""

    def vision_completion(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        """Por padrao, multimodalidade reutiliza a API de chat."""

        return self.chat_completion(model, messages, temperature, max_tokens)
