from typing import Any

import requests

from .base import BaseProvider, CompletionResult, Message, ProviderError


class VLLMProvider(BaseProvider):
    """Provider para o servidor OpenAI-compatible exposto pelo vLLM."""

    name = "vllm"

    def __init__(self, base_url: str, api_key: str, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def health_check(self) -> bool:
        """Consulta a listagem de modelos conforme a API OpenAI-compatible."""

        try:
            resposta = self.session.get(f"{self.base_url}/models", timeout=10)
            return resposta.status_code == 200
        except requests.RequestException:
            return False

    def chat_completion(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        structured: bool = False,
    ) -> CompletionResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        resultado = self._post_chat_completion(payload)
        choices = resultado.get("choices") or []
        if not choices:
            raise ProviderError(502, "O vLLM retornou uma resposta sem choices.")

        message = choices[0].get("message") or {}
        resposta = self._normalizar_conteudo(message.get("content", ""))
        usage = resultado.get("usage") or {}
        metadados = {
            "provider": self.name,
            "id": resultado.get("id"),
            "finish_reason": choices[0].get("finish_reason"),
            "usage": usage,
            # Mantem equivalentes uteis aos contadores anteriormente expostos pelo Ollama.
            "prompt_eval_count": usage.get("prompt_tokens"),
            "eval_count": usage.get("completion_tokens"),
        }
        return CompletionResult(model=model, resposta=resposta, metadados=metadados)

    def _post_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resposta = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.timeout,
            )
            resposta.raise_for_status()
            return resposta.json()
        except requests.Timeout as exc:
            raise ProviderError(504, "Tempo limite excedido ao chamar o vLLM.") from exc
        except requests.HTTPError as exc:
            raise ProviderError(
                502,
                self._extrair_erro(resposta, "Erro HTTP ao chamar o vLLM."),
            ) from exc
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError(502, "Nao foi possivel conectar ao vLLM.") from exc

    @staticmethod
    def _normalizar_conteudo(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                parte.get("text", "")
                for parte in content
                if isinstance(parte, dict) and parte.get("type") == "text"
            )
        return str(content)

    @staticmethod
    def _extrair_erro(resposta: requests.Response, fallback: str) -> str:
        try:
            erro = resposta.json().get("error", fallback)
            if isinstance(erro, dict):
                return str(erro.get("message", fallback))
            return str(erro)
        except ValueError:
            return fallback
