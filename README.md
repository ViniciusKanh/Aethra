<div align="center">

# Aethra

### IA documental privada, com histórico e fontes verificáveis

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Ollama-LLM_local-black)](https://ollama.com/)
[![Turso](https://img.shields.io/badge/Turso-libSQL-4FF8D2)](https://turso.tech/)

Aethra conversa com os documentos da empresa usando um modelo local. Cada resposta
documental inclui os arquivos e trechos usados como evidência.

</div>

## O que está incluído

- Login, cadastro, sessões seguras e perfis `admin` e `user`.
- Usuários, conversas e mensagens persistidos no Turso.
- Credenciais do Turso e Google Drive criptografadas no backend e nunca devolvidas ao navegador.
- Google Drive em modo somente leitura, com busca recursiva em pastas.
- Leitura de PDF, DOCX, TXT, Markdown, CSV, JSON, HTML, XML, YAML e LOG.
- RAG local com LangChain, Chroma, embeddings Ollama e recuperação combinada por relevância + MMR.
- Respostas com arquivo, localização, trecho e link para a fonte.
- Histórico privado: cada usuário acessa somente as próprias conversas.
- Console administrativo invisível para usuários comuns.
- Frontend React + Vite + TypeScript, com Markdown/GFM seguro e bundle estático.

## Arquitetura

```text
Navegador
   |
   v
Aethra / FastAPI :8081
   |-- Turso
   |     `-- usuários, sessões, conversas e mensagens
   |-- Google Drive API (somente leitura)
   |     `-- documentos -> extração -> Chroma local
   `-- Ollama :11434
         |-- qwen3.5:9b
         `-- qwen3-embedding:0.6b
```

O frontend usa React + Vite + TypeScript. O código-fonte vive em `frontend/src`, o
bundle local em `frontend/dist`, a publicação do GitHub Pages em `docs/` e o Space
recebe apenas o bundle compilado em `aethra/frontend/`.

## Instalação local

```powershell
cd "E:\Modelos LLMs\Aethra"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item backend\.env.example backend\.env
ollama pull qwen3.5:9b
ollama pull qwen3-embedding:0.6b
Set-Location frontend
npm install
npm run build
Set-Location ..
uvicorn backend.app.main:app --host 127.0.0.1 --port 8081 --reload
```

Abra `http://127.0.0.1:8081/app/`.

## Primeiro acesso e Turso

1. Crie um banco no Turso e gere um token novo.
2. Abra a tela inicial da Aethra.
3. Informe a URL `libsql://...`, o token novo e os dados do administrador.
4. Clique em **Ativar Aethra**.

O backend cria automaticamente as tabelas de usuários, sessões, conversas e mensagens.
Depois do primeiro acesso, o administrador pode trocar a URL ou o token em
**Administração > Sistema**. O token atual nunca é mostrado no frontend.

Também é possível fornecer `TURSO_DATABASE_URL` e `TURSO_AUTH_TOKEN` no ambiente.
Não versione o arquivo `.env` e revogue imediatamente qualquer token que tenha sido
publicado em chat, log, captura de tela ou repositório.

## Conectar uma pasta do Google Drive

1. No Google Cloud, habilite a Google Drive API e crie uma service account.
2. Gere uma chave JSON para essa conta.
3. Compartilhe a pasta desejada com o e-mail da service account como **Leitor**.
4. Na Aethra, entre como administrador e abra **Administração > Base de conhecimento**.
5. Informe o ID da pasta, cole o JSON e salve.
6. Use **Testar acesso** e depois **Sincronizar documentos**.

O ID é o trecho depois de `/folders/` na URL do Drive. Subpastas são percorridas
automaticamente. Arquivos alterados entram na base na próxima sincronização.

PDFs digitalizados apenas como imagem ainda precisam de OCR antes de serem indexados.

## Perfis de acesso

- `user`: chat, citações e o próprio histórico.
- `admin`: tudo do perfil comum, configuração documental, runtime e gestão de usuários.

O primeiro usuário criado pelo fluxo de ativação é administrador. Novos cadastros
recebem o perfil comum.

## Rotas principais

| Método | Rota | Uso |
|---|---|---|
| `GET` | `/auth/status` | Estado do primeiro acesso |
| `POST` | `/auth/setup` | Configura Turso e cria o primeiro admin |
| `POST` | `/auth/login` | Abre sessão |
| `POST` | `/assistant/chat` | Resposta documental com citações |
| `GET` | `/conversations` | Histórico do usuário autenticado |
| `GET` | `/conversations/{id}` | Mensagens de uma conversa própria |
| `DELETE` | `/conversations/{id}` | Exclui uma conversa própria |
| `GET` | `/admin/config` | Configuração sanitizada para admin |
| `PUT` | `/admin/turso/config` | Troca URL ou token do Turso |
| `PUT` | `/admin/knowledge/config` | Configura a pasta documental |
| `POST` | `/admin/knowledge/sync` | Recria o índice local |
| `GET` | `/admin/users` | Lista usuários para administração |

## Segurança

- Senhas usam Argon2 e nunca são armazenadas em texto puro.
- Tokens de sessão são opacos e persistidos apenas como hash.
- Há bloqueio temporário após tentativas repetidas de login.
- Segredos de integração são criptografados com uma chave local separada.
- A API do Drive usa escopo `drive.readonly`.
- As consultas usam parâmetros vinculados ao enviar dados ao Turso.
- Respostas administrativas indicam apenas se a credencial existe.

Em produção, mantenha `CONFIG_KEY_PATH` em volume persistente e protegido. Sem essa
chave, as credenciais já cifradas não podem ser recuperadas.

## Testes

```powershell
python -m compileall backend tests
python -m unittest discover -s tests -v
Set-Location frontend
npm run typecheck
npm run build
```

Os testes cobrem autenticação, isolamento do histórico, criptografia de configuração,
contrato Turso, extração de documentos, recuperação diversa, citações e o bundle React.
