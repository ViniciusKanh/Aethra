# Checklist de execução do Aethra com vLLM

## 1. Subir o vLLM
Exemplo:
```bash
vllm serve "C:\CAMINHO\PARA\O\MODELO" --host 0.0.0.0 --port 8000
```

## 2. Configurar o backend
Arquivo `.env`:
```env
PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=EMPTY
DEFAULT_CHAT_MODEL=meta-llama/Llama-4-Scout-17B-16E-Instruct
DEFAULT_VISION_MODEL=meta-llama/Llama-4-Scout-17B-16E-Instruct
REQUEST_TIMEOUT=300
```

## 3. Rodar o backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8081
```

## 4. Testar
- `/health`
- `/chat`
- `/summarize`
- `/vision`

## Observação
Se estiver em Windows puro e o vLLM não rodar nativamente no ambiente atual, use Linux/WSL2 para o serving do modelo.
