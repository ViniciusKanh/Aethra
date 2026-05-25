# Aethra

API FastAPI para chat, resumo e visao, com provider desacoplado. O provider
padrao e o servidor OpenAI-compatible do vLLM; o adapter Ollama permanece
disponivel por configuracao.

## Estrutura

```text
Aethra/
|-- backend/
|   |-- .env.example
|   `-- app/
|       |-- config/
|       |   `-- config.py
|       |-- models/
|       |   `-- schemas.py
|       |-- providers/
|       |   |-- base.py
|       |   |-- factory.py
|       |   |-- ollama_provider.py
|       |   `-- vllm_provider.py
|       |-- routes/
|       |   |-- chat.py
|       |   |-- health.py
|       |   |-- summarize.py
|       |   `-- vision.py
|       |-- services/
|       |   |-- chat_service.py
|       |   |-- summarize_service.py
|       |   `-- vision_service.py
|       `-- main.py
|-- frontend/
`-- requirements.txt
```

## Arquitetura

- `routes`: contrato HTTP publico e documentacao automatica em `/docs`.
- `services`: prompts e casos de uso de chat, resumo e multimodalidade.
- `providers`: integracao com engines de inferencia; vLLM e Ollama implementam
  o mesmo contrato.
- `config`: selecao do provider, modelos e endpoints por variaveis de ambiente.

As rotas publicas permanecem `GET /health`, `POST /chat`,
`POST /summarize` e `POST /vision`. O campo legado `ollama` de `/health`
foi mantido e reflete o status do provider ativo; novos clientes devem usar
`provider` e `provider_status`.

## Configuracao

Na raiz do projeto:

```powershell
Copy-Item backend/.env.example backend/.env
```

Configuracao padrao:

```dotenv
PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=EMPTY
DEFAULT_CHAT_MODEL=meta-llama/Llama-4-Scout-17B-16E-Instruct
DEFAULT_VISION_MODEL=meta-llama/Llama-4-Scout-17B-16E-Instruct
REQUEST_TIMEOUT=300
APP_NAME=Aethra API
APP_VERSION=1.0.0
APP_DESCRIPTION=API da Aethra para chat, resumo e visao
```

`DEFAULT_CHAT_MODEL` e `DEFAULT_VISION_MODEL` devem corresponder ao nome
exposto pelo vLLM. O armazenamento do modelo pode mudar sem alterar o codigo:
basta iniciar o vLLM com o novo path e manter ou ajustar
`--served-model-name` e o `.env`.

## Producao Com Ollama

Para sistemas terceiros, publique somente a API Aethra. Mantenha o Ollama
escutando em `127.0.0.1:11434`, sem expor essa porta na rede ou na internet.

O fluxo recomendado e:

```text
Sistema terceiro -> HTTPS + X-API-Key -> Caddy -> Aethra :8080 -> Ollama :11434
```

O arquivo `deployment/.env.production.example` contem um modelo de
configuracao para Ollama. Gere uma chave segura no PowerShell:

```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
[Convert]::ToBase64String($bytes)
```

No servidor, crie `backend/.env` a partir do modelo e substitua `API_KEY`.
Esse arquivo contem segredo e nao deve ser commitado. Como versoes iniciais
deste projeto rastreavam `backend/.env`, remova-o do indice Git antes de
inserir qualquer chave real:

```powershell
git rm --cached backend/.env
```

Outra opcao e configurar essas variaveis diretamente no servico Windows que
executara a API, sem gravar a chave dentro do repositorio.

```dotenv
ENVIRONMENT=production
API_KEY=<CHAVE_GERADA>
CORS_ORIGINS=
ENABLE_DOCS=false

PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
DEFAULT_CHAT_MODEL=llama3.2:3b
DEFAULT_VISION_MODEL=llava:7b
REQUEST_TIMEOUT=300
```

`CORS_ORIGINS` pode ficar vazio quando somente backends consumirem a API. Se
um aplicativo web autorizado fizer chamadas diretamente do navegador, informe
as origens separadas por virgula, por exemplo
`https://portal.exemplo.com.br,https://admin.exemplo.com.br`.

Inicie a Aethra sem `--reload`, vinculada apenas ao host local:

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
```

Coloque HTTPS na frente da Aethra usando um proxy reverso. Com Caddy, copie
`deployment/Caddyfile.example`, substitua o dominio e execute:

```powershell
Copy-Item deployment\Caddyfile.example deployment\Caddyfile
# Edite deployment\Caddyfile e substitua api.exemplo.com.br pelo seu dominio.
caddy run --config deployment\Caddyfile
```

O dominio deve apontar para o servidor e as portas `80` e `443` devem chegar
ao Caddy. Em uma instalacao permanente, execute Ollama, Aethra e Caddy como
servicos que iniciam com o Windows e reiniciam em caso de falha.

Chamadas autenticadas de um sistema terceiro:

```powershell
$headers = @{ "X-API-Key" = "<CHAVE_GERADA>" }
$body = @{
  texto = "Conteudo do e-mail recebido pelo sistema integrador."
  instrucoes = "Resuma, classifique a prioridade e indique a proxima acao."
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "https://api.exemplo.com.br/summarize" `
  -Method Post `
  -Headers $headers `
  -ContentType "application/json; charset=utf-8" `
  -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Em producao, `/chat`, `/summarize` e `/vision` retornam `401` quando
`X-API-Key` estiver ausente ou incorreto. `/health` permanece publico para
monitoramento. Com `ENABLE_DOCS=false`, `/docs` e `/openapi.json` nao ficam
publicos.

## Executar

O vLLM nao tem suporte nativo oficial a Windows. Em uma instalacao oficial
via WSL/Linux, o path atual em `D:` normalmente aparece como:

```bash
/mnt/d/Modelos LLMs/Llama-4-Scout-17B-16E-Instruct
```

Se esse diretorio estiver em um formato carregavel pela versao instalada do
vLLM, o serving pode ser iniciado na porta `8000` assim:

```bash
vllm serve "/mnt/d/Modelos LLMs/Llama-4-Scout-17B-16E-Instruct" \
  --served-model-name meta-llama/Llama-4-Scout-17B-16E-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --limit-mm-per-prompt '{"image": 1}'
```

O diretorio local observado contem checkpoints `.pth` no formato original. As
receitas oficiais do Scout para vLLM usam variantes preparadas para serving.
Caso a versao instalada do vLLM nao aceite esses artefatos, use um diretorio
convertido/compativel ou um model ID autorizado no servidor; a API da Aethra
nao precisa mudar.

Instale e execute a Aethra em outra porta, pois `8000` esta reservada para o
vLLM:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8080
```

- Swagger: <http://localhost:8080/docs>
- Frontend opcional: execute `python -m http.server 5500` dentro de `frontend/`

## Chamadas HTTP

Health check:

```bash
curl http://localhost:8080/health
```

Chat:

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"pergunta":"Explique o motivo mais comum de churn em NPS baixo.","temperatura":0.2}'
```

Resumo de ticket, e-mail ou NPS:

```bash
curl -X POST http://localhost:8080/summarize \
  -H "Content-Type: application/json" \
  -d '{"texto":"Cliente relata cobranca duplicada e aguarda retorno ha 3 dias.","instrucoes":"Resuma o ticket e indique a acao recomendada."}'
```

Visao com imagem base64:

```bash
curl -X POST http://localhost:8080/vision \
  -H "Content-Type: application/json" \
  -d '{"imagem_base64":"<BASE64_DA_IMAGEM>","imagem_media_type":"image/jpeg","prompt":"Descreva esta imagem."}'
```

Para retornar temporariamente ao provider anterior:

```dotenv
PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_CHAT_MODEL=llama3.1:8b
DEFAULT_VISION_MODEL=llava:7b
```
