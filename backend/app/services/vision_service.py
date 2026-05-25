import base64
import binascii

from ..config import Settings
from ..models import TextTaskResponse, VisionRequest
from ..providers import BaseProvider


class VisionService:
    """Monta mensagens multimodais no formato OpenAI Vision."""

    SYSTEM_PROMPT = (
        "Voce e um assistente de visao computacional. "
        "Descreva e interprete a imagem com objetividade em portugues do Brasil."
    )

    def __init__(self, provider: BaseProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    def executar(self, payload: VisionRequest) -> TextTaskResponse:
        self._validar_imagem(payload.imagem_base64, payload.imagem_media_type)
        model = payload.model or self.settings.default_vision_model
        data_url = f"data:{payload.imagem_media_type};base64,{payload.imagem_base64}"

        resultado = self.provider.vision_completion(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": payload.prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=payload.max_tokens,
        )
        return TextTaskResponse(
            status="ok",
            model=resultado.model,
            resposta=resultado.resposta,
            metadados=resultado.metadados,
        )

    @staticmethod
    def _validar_imagem(imagem_base64: str, media_type: str) -> None:
        if not media_type.startswith("image/"):
            raise ValueError("O imagem_media_type informado deve iniciar com image/.")
        try:
            base64.b64decode(imagem_base64, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("A imagem_base64 informada e invalida.") from exc
