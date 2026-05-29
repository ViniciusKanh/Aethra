from ..config import Settings
from ..models import EmailSummarizeRequest, SummarizeRequest, TextTaskResponse
from ..providers import BaseProvider


class SummarizeService:
    """Cria prompts consistentes para e-mails, NPS, tickets e textos gerais."""

    SYSTEM_PROMPT = (
        "Voce e um especialista em sumarizacao empresarial. "
        "Resuma em portugues do Brasil com fidelidade, clareza e objetividade. "
        "Quando pertinente, destaque tema central, sentimento, problemas, acoes "
        "ou proximos passos sem inventar informacoes."
    )
    EMAIL_SYSTEM_PROMPT = (
        "Voce e um analista de atendimento e operacoes. "
        "Analise e-mails recebidos em portugues do Brasil com foco em resumo, "
        "prioridade, problema principal e proxima acao. "
        "Nao invente dados ausentes e indique quando uma informacao nao estiver no texto."
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

    def executar_email(self, payload: EmailSummarizeRequest) -> TextTaskResponse:
        """Resumo especializado para e-mails com campos simples para integracoes."""

        model = payload.model or self.settings.default_chat_model
        contexto = self._montar_contexto_email(payload)
        prompt = (
            "Tarefa: analisar e resumir o e-mail abaixo.\n\n"
            "Formato da resposta:\n"
            "1. Resumo\n"
            "2. Problema principal\n"
            "3. Prioridade: baixa, media, alta ou critica\n"
            "4. Acao recomendada\n"
            "5. Observacoes relevantes\n\n"
            f"Instrucoes adicionais:\n{payload.instrucoes}\n\n"
            f"E-mail:\n{contexto}"
        )
        resultado = self.provider.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": self.EMAIL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
            max_tokens=payload.max_tokens,
        )
        metadados = dict(resultado.metadados)
        metadados["tipo_resumo"] = "email"
        return TextTaskResponse(
            status="ok",
            model=resultado.model,
            resposta=resultado.resposta,
            metadados=metadados,
        )

    @staticmethod
    def _montar_contexto_email(payload: EmailSummarizeRequest) -> str:
        """Agrupa campos opcionais sem obrigar o cliente a montar um prompt."""

        partes: list[str] = []
        if payload.assunto:
            partes.append(f"Assunto: {payload.assunto.strip()}")
        if payload.remetente:
            partes.append(f"Remetente: {payload.remetente.strip()}")
        partes.append(f"Corpo:\n{payload.corpo.strip()}")
        return "\n\n".join(partes)
