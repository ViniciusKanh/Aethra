# Aethra — handoff técnico

Atualizado em 2026-07-06.

## Estado atual

- Aethra é um chatbot documental. A integração analítica anterior foi removida.
- Backend FastAPI com provider Ollama local.
- Modelo de chat local: `qwen3.5:9b`.
- Embeddings locais: `qwen3-embedding:0.6b`.
- Google Drive somente leitura com ingestão recursiva.
- Formatos: PDF, DOCX, TXT, Markdown, CSV, JSON, HTML, XML, YAML e LOG.
- Respostas documentais retornam arquivo, localização, trecho e link.
- Turso persiste usuários, sessões, conversas e mensagens.
- SQLite local guarda somente configuração criptografada e estado do índice.
- Perfis: usuário acessa chat/histórico próprio; admin acessa também configuração e usuários.
- Frontend React + Vite + TypeScript em `frontend/src`, compilado em `frontend/dist`.
- Bundle estático sincronizado em `docs/` e `aethra/frontend/`.
- Respostas usam Markdown/GFM seguro e o RAG combina relevância vetorial com MMR.

## Execução local

```powershell
cd "E:\Modelos LLMs\Aethra"
pip install -r requirements.txt
ollama serve
uvicorn backend.app.main:app --host 127.0.0.1 --port 8081
```

Interface: `http://127.0.0.1:8081/app/`.

No primeiro acesso, informe uma URL Turso, um token novo e os dados do administrador.
Depois, configure a pasta e a service account do Drive em **Administração > Base de conhecimento**.

## Validação

```powershell
python -m compileall backend tests
python -m unittest discover -s tests -v
Set-Location frontend
npm run typecheck
npm run build
Set-Location ..
git diff --check
```

Última validação: 18 testes aprovados, build React aprovado, API e Ollama online. A pasta documental
configurada foi sincronizada com 36 PDFs, 807 páginas e 3.005 trechos.

## Repositórios

- Principal: `E:\Modelos LLMs\Aethra`
- Space: `E:\Modelos LLMs\Aethra\aethra`

As mudanças estão apenas no workspace; não houve commit, push ou deploy automático.
