# Aethra

Estrutura inicial da sua GenAI com frontend separado do backend.

## Estrutura

```text
Aethra/
├── backend/
│   ├── .env.example
│   └── app/
│       ├── main.py
│       ├── config/
│       ├── models/
│       ├── routes/
│       └── services/
├── frontend/
│   ├── assets/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── requirements.txt
└── README.md
```

## 1. Instalação

Crie e ative seu ambiente virtual, depois instale as dependências:

```bash
pip install -r requirements.txt
```

## 2. Configuração

Copie o arquivo de exemplo:

```bash
cp backend/.env.example backend/.env
```

No Windows PowerShell:

```powershell
Copy-Item backend/.env.example backend/.env
```

## 3. Rodar a API

Na raiz do projeto:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Rodar o frontend

Na pasta `frontend`, suba um servidor simples:

```bash
python -m http.server 5500
```

Abra no navegador:

- Frontend: http://localhost:5500
- Docs da API: http://localhost:8000/docs

## 5. Modelos do Ollama

Para texto:

```bash
ollama pull llama3.1:8b
```

Para visão:

```bash
ollama pull llava:7b
```

## Próximo passo recomendado

Separar o `main.py` em:

- `routes/`
- `services/`
- `models/`
- `config/`

Porque projeto bom cresce com estrutura. Projeto sem estrutura cresce que nem mato.
