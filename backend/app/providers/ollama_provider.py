from typing import Any

import requests

from .base import BaseProvider, CompletionResult, Message, ProviderError


class OllamaProvider(BaseProvider):
    """Provider legado mantido para troca controlada por configuracao."""

    name = "ollama"

    def __init__(self, base_url: str, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health_check(self) -> bool:
        try:
            resposta = requests.get(f"{self.base_url}/api/tags", timeout=10)
            return resposta.status_code == 200
        except requests.RequestException:
            return False

    def chat_completion(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        system, prompt, images = self._converter_messages(messages)
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        resultado = self._generate(payload)
        metadados = {
            "provider": self.name,
            "done": resultado.get("done"),
            "total_duration": resultado.get("total_duration"),
            "load_duration": resultado.get("load_duration"),
            "prompt_eval_count": resultado.get("prompt_eval_count"),
            "eval_count": resultado.get("eval_count"),
        }
        return CompletionResult(
            model=model,
            resposta=resultado.get("response", ""),
            metadados=metadados,
        )

    def _generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resposta = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            resposta.raise_for_status()
            return resposta.json()
        except requests.Timeout as exc:
            raise ProviderError(504, "Tempo limite excedido ao chamar o Ollama.") from exc
        except requests.HTTPError as exc:
            raise ProviderError(
                502,
                self._extrair_erro(resposta, "Erro HTTP ao chamar o Ollama."),
            ) from exc
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError(502, "Nao foi possivel conectar ao Ollama.") from exc

    @staticmethod
    def _converter_messages(messages: list[Message]) -> tuple[str | None, str, list[str]]:
        system: str | None = None
        textos: list[str] = []
        images: list[str] = []
        for message in messages:
            content = message.get("content", "")
            if message.get("role") == "system" and isinstance(content, str):
                system = content
                continue
            if isinstance(content, str):
                textos.append(content)
                continue
            for parte in content:
                if parte.get("type") == "text":
                    textos.append(parte.get("text", ""))
                elif parte.get("type") == "image_url":
                    url = parte.get("image_url", {}).get("url", "")
                    images.append(url.split(",", 1)[-1])
        return system, "\n".join(textos), images

    @staticmethod
    def _extrair_erro(resposta: requests.Response, fallback: str) -> str:
        try:
            return str(resposta.json().get("error", fallback))
        except ValueError:
            return fallback
