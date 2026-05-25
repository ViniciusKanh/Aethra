# Aethra vLLM Backend Refactor Skill

## Objetivo
Esta skill existe para orientar modificações no projeto Aethra com foco em backend FastAPI e serving via vLLM.

## Missão
Ao trabalhar neste projeto, sempre priorize:
1. arquitetura API-first;
2. provider desacoplado;
3. compatibilidade com vLLM OpenAI-compatible;
4. rotas estáveis;
5. código pronto para produção inicial.

## Regras de arquitetura
- Nunca misture lógica de rota com lógica de provider.
- Toda chamada ao modelo deve passar por uma camada de provider.
- Toda lógica de negócio deve ficar em `services/`.
- Toda validação de entrada e saída deve usar Pydantic.
- Toda configuração deve vir de variáveis de ambiente centralizadas em `config/`.
- A API pública deve manter, no mínimo:
  - `GET /health`
  - `POST /chat`
  - `POST /summarize`
  - `POST /vision`

## Provider padrão
Quando o provider for `vllm`, use:
- `GET {VLLM_BASE_URL}/models` para health check
- `POST {VLLM_BASE_URL}/chat/completions` para geração textual e multimodal

## Convenções
- Comentários sempre em Português do Brasil.
- Tipagem explícita sempre que razoável.
- Tratamento de exceções obrigatório.
- Nunca devolver stack trace cru para o cliente da API.
- Retornar mensagens de erro objetivas.

## Estrutura-alvo
backend/
  app/
    main.py
    config/
    models/
    providers/
    routes/
    services/

## Estratégia de resumo
- Usar `chat/completions`.
- Aplicar system prompt especializado em sumarização.
- Permitir instruções opcionais do usuário.
- Priorizar fidelidade, concisão e clareza.

## Estratégia de visão
- Usar mensagem multimodal compatível com o padrão OpenAI.
- Estruturar `messages[].content` como lista de blocos.
- Suportar `text` e `image_url`.

## Checklist mínimo antes de concluir
- [ ] Provider vLLM implementado
- [ ] Configuração via `.env`
- [ ] Health check funcional
- [ ] Rotas preservadas
- [ ] `requirements.txt` atualizado
- [ ] `.env.example` criado
- [ ] exemplos `curl` fornecidos
- [ ] instruções de execução documentadas
