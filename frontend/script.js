const API_BASE_URL = "http://localhost:8000";

function adicionarMensagem(tipo, texto) {
  const chat = document.getElementById("chat");
  const div = document.createElement("div");
  div.className = `message ${tipo}`;
  div.textContent = texto;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function limparChat() {
  const chat = document.getElementById("chat");
  chat.innerHTML = "";
  adicionarMensagem("ai", "Chat limpo. Bora continuar.");
}

async function verificarStatus() {
  const statusEl = document.getElementById("api-status");
  const chatModelEl = document.getElementById("chat-model");
  const visionModelEl = document.getElementById("vision-model");

  statusEl.textContent = "Verificando...";

  try {
    const resposta = await fetch(`${API_BASE_URL}/health`);
    const dados = await resposta.json();

    statusEl.textContent = `${dados.status} | Ollama: ${dados.ollama}`;
    chatModelEl.textContent = dados.default_chat_model;
    visionModelEl.textContent = dados.default_vision_model;
  } catch (erro) {
    statusEl.textContent = "Erro ao conectar";
    chatModelEl.textContent = "-";
    visionModelEl.textContent = "-";
    console.error(erro);
  }
}

async function enviarMensagem() {
  const input = document.getElementById("prompt");
  const texto = input.value.trim();

  if (!texto) {
    return;
  }

  adicionarMensagem("user", texto);
  input.value = "";
  adicionarMensagem("ai", "Pensando...");

  try {
    const resposta = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        pergunta: texto
      })
    });

    const dados = await resposta.json();
    const chat = document.getElementById("chat");
    chat.lastChild.textContent = dados.resposta || "Sem resposta do modelo.";
  } catch (erro) {
    const chat = document.getElementById("chat");
    chat.lastChild.textContent = "Erro ao consultar a API da Aethra.";
    console.error(erro);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  verificarStatus();
});
