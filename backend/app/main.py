from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import os
import base64
import requests


# ============================================================
# Carrega variáveis de ambiente do arquivo .env
# ============================================================
load_dotenv()


# ============================================================
# Configurações
# ============================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "llama3.1:8b")
DEFAULT_VISION_MODEL = os.getenv("DEFAULT_VISION_MODEL", "llava:7b")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "180"))
APP_NAME = os.getenv("APP_NAME", "Aethra API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    "API para chat, resumo, interpretação de imagem e verificação de status."
)


# ============================================================
# Aplicação FastAPI
# ============================================================
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
)


# ============================================================
# CORS
# Em produção, troque ["*"] pelo domínio real do frontend.
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Schemas
# ============================================================
class RootResponse(BaseModel):
    mensagem: str
    docs: str
    status: str


class HealthResponse(BaseModel):
    status: str
    api: str
    ollama: str
    default_chat_model: str
    default_vision_model: str


class ChatRequest(BaseModel):
    pergunta: str = Field(..., min_length=1, description="Pergunta enviada pelo usuário")
    system_prompt: Optional[str] = Field(
        default="Você é um assistente técnico, objetivo e útil. Responda em português do Brasil.",
        description="Prompt de sistema opcional"
    )
    model: Optional[str] = Field(default=DEFAULT_CHAT_MODEL, description="Modelo do Ollama")
    temperatura: Optional[float] = Field(default=0.2, ge=0.0, le=2.0)


class SummarizeRequest(BaseModel):
    texto: str = Field(..., min_length=1, description="Texto a ser resumido")
    instrucoes: Optional[str] = Field(
        default="Resuma o texto de forma objetiva, preservando os pontos principais.",
        description="Instruções adicionais para o resumo"
    )
    model: Optional[str] = Field(default=DEFAULT_CHAT_MODEL, description="Modelo do Ollama")


class VisionRequest(BaseModel):
    imagem_base64: str = Field(..., description="Imagem em base64 sem prefixo data:image")
    prompt: Optional[str] = Field(
        default="Descreva a imagem e interprete seus elementos principais em português do Brasil.",
        description="Prompt da análise visual"
    )
    model: Optional[str] = Field(default=DEFAULT_VISION_MODEL, description="Modelo visual do Ollama")


class TextTaskResponse(BaseModel):
    status: str
    model: str
    resposta: str
    metadados: Dict[str, Any]


# ============================================================
# Funções auxiliares
# ============================================================
def verificar_ollama() -> bool:
    """Verifica se o Ollama está online."""
    try:
        resposta = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        return resposta.status_code == 200
    except requests.RequestException:
        return False


def validar_base64_imagem(imagem_base64: str) -> str:
    """Valida a string base64 recebida."""
    try:
        base64.b64decode(imagem_base64, validate=True)
        return imagem_base64
    except Exception as exc:
        raise HTTPException(status_code=400, detail="A imagem_base64 informada é inválida.") from exc


def extrair_metadados_ollama(resultado: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai metadados úteis da resposta do Ollama."""
    return {
        "done": resultado.get("done"),
        "total_duration": resultado.get("total_duration"),
        "load_duration": resultado.get("load_duration"),
        "prompt_eval_count": resultado.get("prompt_eval_count"),
        "eval_count": resultado.get("eval_count"),
    }


def chamar_ollama_generate(
    model: str,
    prompt: str,
    system: Optional[str] = None,
    images: Optional[List[str]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Chama o endpoint /api/generate do Ollama.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    if system:
        payload["system"] = system

    if images:
        payload["images"] = images

    if options:
        payload["options"] = options

    try:
        resposta = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        resposta.raise_for_status()
        return resposta.json()
    except requests.HTTPError as exc:
        detalhe = "Erro HTTP ao chamar o Ollama."
        try:
            detalhe_json = resposta.json()
            detalhe = detalhe_json.get("error", detalhe)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detalhe) from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Não foi possível conectar ao Ollama.") from exc


# ============================================================
# Rotas
# ============================================================
@app.get("/", response_model=RootResponse, tags=["Base"])
def raiz() -> RootResponse:
    return RootResponse(
        mensagem="API da Aethra online.",
        docs="/docs",
        status="ok",
    )


@app.get("/health", response_model=HealthResponse, tags=["Monitoramento"])
def health() -> HealthResponse:
    ollama_ok = verificar_ollama()
    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        api="online",
        ollama="online" if ollama_ok else "offline",
        default_chat_model=DEFAULT_CHAT_MODEL,
        default_vision_model=DEFAULT_VISION_MODEL,
    )


@app.post("/chat", response_model=TextTaskResponse, tags=["Chat"])
def chat(payload: ChatRequest) -> TextTaskResponse:
    resultado = chamar_ollama_generate(
        model=payload.model or DEFAULT_CHAT_MODEL,
        prompt=payload.pergunta,
        system=payload.system_prompt,
        options={"temperature": payload.temperatura},
    )

    return TextTaskResponse(
        status="ok",
        model=payload.model or DEFAULT_CHAT_MODEL,
        resposta=resultado.get("response", ""),
        metadados=extrair_metadados_ollama(resultado),
    )


@app.post("/summarize", response_model=TextTaskResponse, tags=["Resumo"])
def summarize(payload: SummarizeRequest) -> TextTaskResponse:
    prompt_resumo = f"""
Tarefa: gerar um resumo fiel e objetivo.

Instruções:
{payload.instrucoes}

Texto de entrada:
{payload.texto}
""".strip()

    resultado = chamar_ollama_generate(
        model=payload.model or DEFAULT_CHAT_MODEL,
        prompt=prompt_resumo,
        system="Você é um especialista em sumarização. Resuma em português do Brasil com clareza e fidelidade ao conteúdo.",
        options={"temperature": 0.2},
    )

    return TextTaskResponse(
        status="ok",
        model=payload.model or DEFAULT_CHAT_MODEL,
        resposta=resultado.get("response", ""),
        metadados=extrair_metadados_ollama(resultado),
    )


@app.post("/vision", response_model=TextTaskResponse, tags=["Visão"])
def vision(payload: VisionRequest) -> TextTaskResponse:
    imagem_validada = validar_base64_imagem(payload.imagem_base64)

    resultado = chamar_ollama_generate(
        model=payload.model or DEFAULT_VISION_MODEL,
        prompt=payload.prompt,
        system="Você é um assistente de visão computacional. Descreva e interprete a imagem com objetividade em português do Brasil.",
        images=[imagem_validada],
        options={"temperature": 0.2},
    )

    return TextTaskResponse(
        status="ok",
        model=payload.model or DEFAULT_VISION_MODEL,
        resposta=resultado.get("response", ""),
        metadados=extrair_metadados_ollama(resultado),
    )


# ============================================================
# Inicialização local
# Rode com:
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
