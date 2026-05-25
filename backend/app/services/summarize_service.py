from ..config import Settings
from ..models import SummarizeRequest, TextTaskResponse
from ..providers import BaseProvider


class SummarizeService:
    """Cria prompts consistentes para e-mails, NPS, tickets e textos gerais."""

    SYSTEM_PROMPT = (
        "Voce e um especialista em sumarizacao empresarial. "
        "Resuma em portugues do Brasil com fidelidade, clareza e objetividade. "
        "Quando pertinente, destaque tema central, sentimento, problemas, acoes "
        "ou proximos passos sem inventar informacoes."
    )

    def __init__(self, provider: BaseProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    def executar(self, payload: SummarizeRequest) -> TextTaskResponse:
        model = payload.model or self.settings.default_chat_model
        prompt = (
            "Tarefa: gerar um resumo fiel e, quando solicitado, uma explicacao util.\n\n"
            f"Instrucoes:\n{payload.instrucoes}\n\n"
            f"Texto de entrada:\n{payload.texto}"
        )
        resultado = self.provider.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
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
