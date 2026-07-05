<div align="center">

# Aethra

### Intelligence workspace local para GenAI, PostgreSQL, operações e visão multimodal

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black)](https://ollama.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-DW-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Aethra conecta modelos locais, fluxos de atendimento e um Data Warehouse PostgreSQL
em uma API auditável e um workspace web protegido.

</div>

## Capacidades

- Chat e geração de texto.
- Resumo de e-mails, tickets, NPS e textos executivos.
- Análise multimodal de imagens.
- Perguntas em linguagem natural sobre tabelas `fact_` e `dim_`.
- SQL gerado com allowlist, limite de linhas e transação read only.
- Console administrativo separado da API pública.
- Providers Ollama e vLLM.
- Frontend estático publicável pelo GitHub Pages.

## Arquitetura local recomendada

```text
Navegador
   │
   ▼
Aethra / FastAPI :8080
   ├── Ollama :11434
   │      └── qwen3.5:9b
   └── PostgreSQL DW :5432
          └── usuário dedicado somente leitura
```

Para uma RTX 4050 de 6 GB e 32 GB de RAM, `qwen3.5:9b` oferece um equilíbrio
prático entre inteligência e velocidade. O modelo tem suporte a raciocínio,
ferramentas, contexto amplo e visão multimodal. Parte do processamento pode usar
RAM compartilhada quando a VRAM não for suficiente.

## Instalação local

### 1. Dependências

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Instale o Ollama e baixe o modelo:

```powershell
ollama pull qwen3.5:9b
```

### 2. Configuração

```powershell
Copy-Item backend\.env.example backend\.env
```

Configuração mínima local:

```dotenv
ENVIRONMENT=development
AUTH_ENABLED=false
API_KEY=
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:8080
ENABLE_DOCS=true
FRONTEND_ENABLED=true
FRONTEND_DIR=frontend

PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
DEFAULT_CHAT_MODEL=qwen3.5:9b
DEFAULT_VISION_MODEL=qwen3.5:9b
REQUEST_TIMEOUT=300
```

### 3. Administração e Data Warehouse

Gere uma chave administrativa com pelo menos 32 caracteres e configure o DW
apenas em `backend/.env`, que é ignorado pelo Git:

```dotenv
ADMIN_ENABLED=true
ADMIN_API_KEY=UMA_CHAVE_ALEATORIA_COM_32_OU_MAIS_CARACTERES

DW_ENABLED=true
DW_HOST=10.20.9.21
DW_PORT=5432
DW_DATABASE=seu_banco_dw
DW_USER=aethra_reader
DW_PASSWORD=SENHA_LOCAL_NAO_VERSIONADA
DW_SSLMODE=prefer
DW_ALLOWED_SCHEMAS=analytics,public
DW_TABLE_PREFIXES=fact_,dim_
DW_CONNECT_TIMEOUT=5
DW_STATEMENT_TIMEOUT_MS=30000
DW_MAX_ROWS=200
DW_SCHEMA_CACHE_TTL=300
```

Use [deployment/postgres_readonly.sql.example](deployment/postgres_readonly.sql.example)
como referência para criar o papel PostgreSQL com privilégio mínimo.

### 4. Execução

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
```

- Workspace: <http://127.0.0.1:8080/app/>
- Health: <http://127.0.0.1:8080/health>
- Swagger: <http://127.0.0.1:8080/docs>

## Segurança do DW

A proteção é aplicada em várias camadas:

1. `/admin/*` e `/dw/*` exigem `X-Admin-Key`.
2. Chaves e senha PostgreSQL nunca são devolvidas pelo endpoint de configuração.
3. Apenas schemas e prefixos configurados entram no contexto do modelo.
4. O SQL precisa ser uma única query compatível com `SELECT`.
5. Referências fora da allowlist de tabelas são rejeitadas.
6. Operações DDL/DML e funções PostgreSQL perigosas são bloqueadas.
7. Toda conexão usa `default_transaction_read_only=on` e `statement_timeout`.
8. O servidor limita a quantidade de linhas retornadas.
9. A conta PostgreSQL deve possuir somente `CONNECT`, `USAGE` e `SELECT`.

Uma interface escondida não é uma fronteira de segurança. O frontend só revela
as áreas DW e Backend depois que `/admin/config` valida a chave; a autorização
real sempre acontece no FastAPI.

## Endpoints

| Método | Endpoint | Função | Proteção |
| --- | --- | --- | --- |
| `GET` | `/health` | Status da API e provider | Pública |
| `POST` | `/chat` | Chat e geração de texto | API key opcional |
| `POST` | `/summarize` | Resumo geral | API key opcional |
| `POST` | `/summarize/email` | Resumo especializado de e-mail | API key opcional |
| `POST` | `/vision` | Análise de imagem base64 | API key opcional |
| `GET` | `/admin/config` | Configuração saneada do backend | Admin |
| `POST` | `/admin/dw/test` | Teste de conexão PostgreSQL | Admin |
| `GET` | `/admin/dw/schema` | Tabelas e colunas permitidas | Admin |
| `POST` | `/dw/ask` | Pergunta, SQL, execução e síntese | Admin |

### Exemplo de pergunta ao DW

```powershell
$headers = @{ "X-Admin-Key" = "SUA_CHAVE_ADMIN" }
$body = @{
  pergunta = "Qual foi a receita mensal por região e onde ocorreu a maior queda?"
  max_rows = 100
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/dw/ask" `
  -Method Post `
  -Headers $headers `
  -ContentType "application/json; charset=utf-8" `
  -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Resposta resumida:

```json
{
  "status": "ok",
  "model": "qwen3.5:9b",
  "resposta": "Síntese baseada nas linhas retornadas...",
  "sql": "SELECT ... LIMIT 100",
  "columns": ["mes", "regiao", "receita"],
  "rows": [],
  "row_count": 0,
  "truncated": false,
  "metadados": {
    "read_only": true
  }
}
```

## Estrutura

```text
Aethra/
├── backend/app/
│   ├── config/
│   ├── models/
│   ├── providers/
│   ├── routes/
│   ├── services/
│   ├── main.py
│   └── security.py
├── deployment/
├── docs/                 # GitHub Pages
├── frontend/             # fonte principal da interface
├── tests/
├── requirements.txt
└── README.md
```

Ao alterar o frontend, sincronize `frontend/` com `docs/` e com o frontend do
repositório separado do Hugging Face Space.

## Testes

```powershell
python -m unittest discover -s tests -v
node --check frontend\script.js
git diff --check
```

Os testes cobrem autenticação administrativa, ausência de segredos nas respostas,
proteção do endpoint DW, bloqueio de escrita, allowlist SQL e contrato entre HTML/JS.

## Limitações atuais

- O modelo não conhece a semântica de negócio que não estiver expressa nos nomes e
  tipos das tabelas. Uma camada semântica com descrições melhora muito a precisão.
- A rede/VPN precisa permitir acesso ao host PostgreSQL.
- O primeiro carregamento de `qwen3.5:9b` usa mais tempo e memória.
- Consultas complexas podem precisar de exemplos validados ou métricas oficiais.
- O Hugging Face CPU continua adequado apenas para demonstração; DW e modelo mais
  capaz devem rodar localmente ou em infraestrutura dedicada.

## Licença

MIT. Consulte [LICENSE](LICENSE).
