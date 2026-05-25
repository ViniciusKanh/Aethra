const DEFAULT_API_URL = "http://localhost:8080";
const STORAGE_KEYS = {
  apiUrl: "aethra.apiUrl",
  apiKey: "aethra.apiKey",
  ngrokHeader: "aethra.ngrokHeader"
};

const state = {
  image: null,
  toastTimer: null
};

const presets = {
  email: {
    instructions: "Resuma este e-mail, identifique o problema principal, a prioridade e a proxima acao recomendada.",
    sample: `Assunto: Cobranca duplicada
De: cliente@empresa.com

Ola, identifiquei duas cobrancas iguais em minha fatura deste mes.
Ja abri um chamado ha tres dias, mas ainda nao tive retorno.
Preciso que uma das cobrancas seja estornada com urgencia.`
  },
  ticket: {
    instructions: "Resuma o ticket, classifique o impacto, indique a causa relatada e proponha o proximo passo de atendimento.",
    sample: `Ticket #8452 - Falha ao emitir nota fiscal
Cliente informa que, desde ontem, pedidos aprovados nao geram nota fiscal.
O erro afeta 18 pedidos e impede o envio das mercadorias.`
  },
  nps: {
    instructions: "Explique o feedback de NPS, identifique sentimento, risco de churn e uma acao de recuperacao.",
    sample: `Nota NPS: 3
Comentario: O produto funciona, mas precisei falar tres vezes com o suporte para resolver uma cobranca incorreta. Nao pretendo renovar se continuar assim.`
  },
  executive: {
    instructions: "Produza um resumo executivo curto com situacao, impacto, urgencia e decisao recomendada.",
    sample: `A equipe comercial reportou aumento de reclamacoes por atraso no retorno.
Foram identificados 42 tickets abertos ha mais de 72 horas, incluindo nove clientes corporativos em renovacao contratual.`
  }
};

function byId(id) {
  return document.getElementById(id);
}

function apiUrl() {
  return byId("api-url").value.trim().replace(/\/+$/, "") || DEFAULT_API_URL;
}

function requestHeaders(includeContentType = true) {
  const headers = {};
  const key = byId("api-key").value.trim();
  if (includeContentType) {
    headers["Content-Type"] = "application/json";
  }
  if (key) {
    headers["X-API-Key"] = key;
  }
  if (byId("ngrok-header").checked) {
    headers["ngrok-skip-browser-warning"] = "1";
  }
  return headers;
}

function persistConnection() {
  sessionStorage.setItem(STORAGE_KEYS.apiUrl, apiUrl());
  sessionStorage.setItem(STORAGE_KEYS.apiKey, byId("api-key").value.trim());
  sessionStorage.setItem(STORAGE_KEYS.ngrokHeader, String(byId("ngrok-header").checked));
  updateIntegrationSnippet();
}

function restoreConnection() {
  byId("api-url").value = sessionStorage.getItem(STORAGE_KEYS.apiUrl) || DEFAULT_API_URL;
  byId("api-key").value = sessionStorage.getItem(STORAGE_KEYS.apiKey) || "";
  byId("ngrok-header").checked = sessionStorage.getItem(STORAGE_KEYS.ngrokHeader) === "true";
}

function showToast(message, isError = false) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3300);
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${apiUrl()}${path}`, {
    method: options.method || "GET",
    headers: requestHeaders(Boolean(options.body)),
    body: options.body ? JSON.stringify(options.body) : undefined
  });

  let payload;
  try {
    payload = await response.json();
  } catch (_error) {
    payload = { detail: "A API retornou uma resposta que nao e JSON." };
  }

  if (!response.ok) {
    const detail = payload.detail || `Erro HTTP ${response.status}`;
    throw new Error(detail);
  }
  return payload;
}

function setStatus(status, text) {
  const pill = byId("header-status");
  pill.className = `status-pill ${status}`;
  pill.querySelector("span:last-child").textContent = text;
}

async function checkHealth() {
  setStatus("waiting", "Verificando");
  byId("api-status").textContent = "Verificando...";
  try {
    const data = await apiRequest("/health");
    const online = data.provider_status === "online";
    setStatus(online ? "" : "offline", online ? "Online" : "Provider offline");
    byId("api-status").textContent = online ? "Online" : "Indisponivel";
    byId("header-provider").textContent = `Provider: ${data.provider}`;
    byId("chat-model").textContent = data.default_chat_model;
    byId("vision-model").textContent = data.default_vision_model;
    byId("vision-panel-model").textContent = data.default_vision_model;
    return true;
  } catch (error) {
    setStatus("offline", "Sem conexao");
    byId("api-status").textContent = "Falha de conexao";
    byId("header-provider").textContent = "Provider: --";
    showToast(`Nao foi possivel conectar: ${error.message}`, true);
    return false;
  }
}

function updateExecution(result, startTime) {
  const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
  byId("last-latency").textContent = `${elapsed}s`;
  byId("last-model").textContent = result.model || "Modelo nao informado";
}

function openTab(tabName) {
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === tabName);
  });
}

function appendMessage(role, content, loading = false) {
  const messages = byId("chat-messages");
  const article = document.createElement("article");
  article.className = `bubble ${role}${loading ? " loading" : ""}`;

  const avatar = document.createElement("span");
  avatar.className = "bubble-avatar";
  avatar.textContent = role === "assistant" ? "A" : "V";

  const wrapper = document.createElement("div");
  const label = document.createElement("small");
  label.textContent = role === "assistant" ? "Aethra" : "Voce";
  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  wrapper.append(label, paragraph);
  article.append(avatar, wrapper);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

async function submitChat(event) {
  event.preventDefault();
  const input = byId("chat-prompt");
  const prompt = input.value.trim();
  if (!prompt) {
    return;
  }

  appendMessage("user", prompt);
  input.value = "";
  const pending = appendMessage("assistant", "Pensando", true);
  const button = byId("chat-submit");
  const start = performance.now();
  button.disabled = true;

  try {
    const result = await apiRequest("/chat", {
      method: "POST",
      body: {
        pergunta: prompt,
        system_prompt: byId("system-prompt").value.trim(),
        temperatura: Number(byId("temperature").value)
      }
    });
    pending.classList.remove("loading");
    pending.querySelector("p").textContent = result.resposta || "Sem resposta do modelo.";
    updateExecution(result, start);
  } catch (error) {
    pending.classList.remove("loading");
    pending.querySelector("p").textContent = `Erro: ${error.message}`;
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

function updateSummaryPreset(loadSample = false) {
  const preset = presets[byId("summary-preset").value];
  byId("summary-instructions").value = preset.instructions;
  if (loadSample) {
    byId("summary-text").value = preset.sample;
    updateSummaryCount();
  }
}

function updateSummaryCount() {
  byId("summary-count").textContent = byId("summary-text").value.length.toLocaleString("pt-BR");
}

async function submitSummary(event) {
  event.preventDefault();
  const output = byId("summary-output");
  const button = byId("summary-submit");
  const start = performance.now();
  output.className = "result-output busy";
  output.textContent = "Gerando resumo...";
  button.disabled = true;

  try {
    const result = await apiRequest("/summarize", {
      method: "POST",
      body: {
        texto: byId("summary-text").value,
        instrucoes: byId("summary-instructions").value
      }
    });
    output.className = "result-output";
    output.textContent = result.resposta || "Sem resposta do modelo.";
    updateExecution(result, start);
  } catch (error) {
    output.className = "result-output";
    output.textContent = `Erro: ${error.message}`;
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

function handleImageFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    showToast("Selecione um arquivo de imagem valido.", true);
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const dataUrl = String(reader.result);
    state.image = {
      base64: dataUrl.split(",")[1],
      mediaType: file.type
    };
    const preview = byId("vision-preview");
    preview.src = dataUrl;
    preview.hidden = false;
    byId("upload-copy").hidden = true;
    byId("vision-submit").disabled = false;
  };
  reader.readAsDataURL(file);
}

async function submitVision(event) {
  event.preventDefault();
  if (!state.image) {
    return;
  }
  const output = byId("vision-output");
  const button = byId("vision-submit");
  const start = performance.now();
  output.className = "result-output busy";
  output.textContent = "Analisando imagem... modelos visuais podem levar mais tempo.";
  button.disabled = true;

  try {
    const result = await apiRequest("/vision", {
      method: "POST",
      body: {
        imagem_base64: state.image.base64,
        imagem_media_type: state.image.mediaType,
        prompt: byId("vision-prompt").value
      }
    });
    output.className = "result-output";
    output.textContent = result.resposta || "Sem interpretacao retornada.";
    updateExecution(result, start);
  } catch (error) {
    output.className = "result-output";
    output.textContent = `Erro: ${error.message}`;
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function copyResult(id) {
  const text = byId(id).innerText;
  try {
    await navigator.clipboard.writeText(text);
    showToast("Conteudo copiado.");
  } catch (_error) {
    showToast("Nao foi possivel copiar neste navegador.", true);
  }
}

function updateIntegrationSnippet() {
  const url = apiUrl();
  byId("integration-code").textContent = `$headers = @{
  "X-API-Key" = "<SUA_CHAVE_PRIVADA>"
  "ngrok-skip-browser-warning" = "1"
}

$body = @{
  texto = "Conteudo do e-mail recebido pelo sistema."
  instrucoes = "Resuma, informe prioridade e proxima acao."
} | ConvertTo-Json

Invoke-RestMethod \`
  -Uri "${url}/summarize" \`
  -Method Post \`
  -Headers $headers \`
  -ContentType "application/json; charset=utf-8" \`
  -Body ([Text.Encoding]::UTF8.GetBytes($body))`;
}

function setupEvents() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => openTab(tab.dataset.tab));
  });
  document.querySelectorAll("[data-open-tab]").forEach((button) => {
    button.addEventListener("click", () => openTab(button.dataset.openTab));
  });

  byId("refresh-status").addEventListener("click", checkHealth);
  byId("test-connection").addEventListener("click", async () => {
    persistConnection();
    if (await checkHealth()) {
      showToast("Conexao com a Aethra confirmada.");
    }
  });
  byId("save-connection").addEventListener("click", () => {
    persistConnection();
    showToast("Configuracao aplicada nesta sessao.");
    checkHealth();
  });
  byId("api-url").addEventListener("input", () => {
    const isNgrok = byId("api-url").value.includes("ngrok");
    if (isNgrok) {
      byId("ngrok-header").checked = true;
    }
    updateIntegrationSnippet();
  });
  byId("toggle-key").addEventListener("click", () => {
    const keyInput = byId("api-key");
    keyInput.type = keyInput.type === "password" ? "text" : "password";
    byId("toggle-key").textContent = keyInput.type === "password" ? "Ver" : "Ocultar";
  });

  byId("chat-form").addEventListener("submit", submitChat);
  byId("clear-chat").addEventListener("click", () => {
    byId("chat-messages").innerHTML = "";
    appendMessage("assistant", "Chat limpo. Como posso ajudar agora?");
  });
  byId("chat-prompt").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      byId("chat-form").requestSubmit();
    }
  });
  byId("temperature").addEventListener("input", (event) => {
    byId("temperature-value").textContent = event.target.value;
  });

  byId("summary-preset").addEventListener("change", () => updateSummaryPreset(false));
  byId("load-sample").addEventListener("click", () => updateSummaryPreset(true));
  byId("summary-text").addEventListener("input", updateSummaryCount);
  byId("summary-form").addEventListener("submit", submitSummary);

  const dropZone = byId("drop-zone");
  byId("vision-file").addEventListener("change", (event) => handleImageFile(event.target.files[0]));
  ["dragenter", "dragover"].forEach((name) => {
    dropZone.addEventListener(name, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    dropZone.addEventListener(name, (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragging");
    });
  });
  dropZone.addEventListener("drop", (event) => handleImageFile(event.dataTransfer.files[0]));
  byId("vision-form").addEventListener("submit", submitVision);

  document.querySelectorAll(".copy-result").forEach((button) => {
    button.addEventListener("click", () => copyResult(button.dataset.copy));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  restoreConnection();
  setupEvents();
  updateIntegrationSnippet();
  updateSummaryCount();
  checkHealth();
});
