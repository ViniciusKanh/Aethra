const HF_SPACE_API_URL = "https://viniciuskhan-aethra.hf.space";

const viewMeta = {
  overview: ["Aethra Workspace", "Visão geral"],
  chat: ["Modelo generativo", "Chat GenAI"],
  warehouse: ["Dados corporativos", "DW Insights"],
  summary: ["Operações", "Resumos inteligentes"],
  vision: ["Multimodal", "Vision Lab"],
  "api-docs": ["Desenvolvimento", "API & Integrações"],
  admin: ["Área restrita", "Configurações do backend"]
};

const presets = {
  email: {
    instructions: "Resuma este e-mail, identifique o problema principal, a prioridade e a próxima ação recomendada.",
    subject: "Cobrança duplicada",
    from: "cliente@empresa.com",
    sample: "Olá, identifiquei duas cobranças iguais em minha fatura deste mês. Já abri um chamado há três dias, mas ainda não tive retorno. Preciso que uma das cobranças seja estornada com urgência."
  },
  ticket: {
    instructions: "Resuma o ticket, classifique o impacto, identifique a causa relatada e proponha o próximo passo.",
    sample: "Ticket #8452 — Falha ao emitir nota fiscal. Desde ontem, pedidos aprovados não geram nota. O erro afeta 18 pedidos e impede o envio das mercadorias."
  },
  nps: {
    instructions: "Explique o feedback, identifique sentimento, risco de churn e uma ação de recuperação.",
    sample: "Nota NPS: 3. O produto funciona, mas precisei falar três vezes com o suporte para resolver uma cobrança incorreta. Não pretendo renovar se continuar assim."
  },
  executive: {
    instructions: "Produza um resumo executivo com situação, impacto, urgência e decisão recomendada.",
    sample: "A equipe comercial reportou aumento de reclamações por atraso no retorno. Há 42 tickets abertos há mais de 72 horas, incluindo nove clientes corporativos em renovação."
  }
};

const state = {
  adminKey: "",
  adminConfig: null,
  image: null,
  pendingAdminView: "admin",
  toastTimer: null
};

function byId(id) {
  return document.getElementById(id);
}

function resolveDefaultApiUrl() {
  const host = window.location.hostname;
  if (!window.location.protocol.startsWith("http")) return "http://localhost:8080";
  if (host.endsWith("github.io")) return HF_SPACE_API_URL;
  if (window.location.pathname.startsWith("/app")) return window.location.origin;
  if (["localhost", "127.0.0.1", "::1"].includes(host)) return "http://localhost:8080";
  return window.location.origin;
}

function apiUrl() {
  return byId("api-url").value.trim().replace(/\/+$/, "") || resolveDefaultApiUrl();
}

function showToast(message, isError = false) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3600);
}

function errorMessage(payload, status) {
  const detail = payload?.detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(" · ");
  if (detail && typeof detail === "object") return detail.message || JSON.stringify(detail);
  return detail || `Erro HTTP ${status}`;
}

async function apiRequest(path, options = {}) {
  const headers = {};
  if (options.body) headers["Content-Type"] = "application/json";
  if (options.admin) {
    if (!state.adminKey) throw new Error("Sessão administrativa não autenticada.");
    headers["X-Admin-Key"] = state.adminKey;
  }
  const response = await fetch(`${apiUrl()}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  let payload;
  try { payload = await response.json(); } catch (_error) { payload = { detail: "A API não retornou JSON." }; }
  if (!response.ok) throw new Error(errorMessage(payload, response.status));
  return payload;
}

function navigate(viewName) {
  if (["warehouse", "admin"].includes(viewName) && !state.adminKey) {
    state.pendingAdminView = viewName;
    openAdminDialog();
    return;
  }
  document.querySelectorAll("[data-view-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.viewPanel === viewName));
  document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === viewName));
  const [kicker, title] = viewMeta[viewName] || viewMeta.overview;
  byId("view-kicker").textContent = kicker;
  byId("view-title").textContent = title;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setHealthVisual(mode, label) {
  const header = byId("header-status");
  header.className = `health-chip ${mode}`.trim();
  header.querySelector("span").textContent = label;
  const dots = [byId("sidebar-status-dot"), byId("runtime-dot")];
  dots.forEach((dot) => { dot.className = `live-dot ${mode}`.trim(); });
  byId("sidebar-status").textContent = label;
}

async function checkHealth() {
  setHealthVisual("waiting", "Verificando");
  try {
    const data = await apiRequest("/health");
    const online = data.provider_status === "online";
    setHealthVisual(online ? "" : "offline", online ? "Online" : "Provider offline");
    byId("provider-chip").textContent = `${data.provider} · ${online ? "ready" : "offline"}`;
    byId("overview-model").textContent = data.default_chat_model;
    byId("overview-provider").textContent = `via ${data.provider}`;
    byId("runtime-api").textContent = "Online";
    byId("runtime-provider").textContent = data.provider;
    byId("runtime-vision").textContent = data.default_vision_model;
    byId("runtime-auth").textContent = data.auth_enabled ? "API privada" : "API aberta";
    byId("chat-context-model").textContent = data.default_chat_model;
    byId("vision-panel-model").textContent = data.default_vision_model;
    return true;
  } catch (error) {
    setHealthVisual("offline", "Sem conexão");
    byId("runtime-api").textContent = "Indisponível";
    byId("provider-chip").textContent = "Provider —";
    showToast(error.message, true);
    return false;
  }
}

function updateExecution(result, startedAt) {
  const elapsed = ((performance.now() - startedAt) / 1000).toFixed(1);
  byId("last-latency").textContent = `${elapsed}s`;
  byId("last-model").textContent = result.model || "Modelo não informado";
}

function appendChatMessage(role, content, loading = false) {
  const article = document.createElement("article");
  article.className = `message ${role}${loading ? " loading" : ""}`;
  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.textContent = role === "assistant" ? "A" : "V";
  const body = document.createElement("div");
  const label = document.createElement("small");
  label.textContent = role === "assistant" ? "Aethra" : "Você";
  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  body.append(label, paragraph);
  article.append(avatar, body);
  byId("chat-messages").appendChild(article);
  byId("chat-messages").scrollTop = byId("chat-messages").scrollHeight;
  return article;
}

async function submitChat(event) {
  event.preventDefault();
  const prompt = byId("chat-prompt").value.trim();
  if (!prompt) return;
  appendChatMessage("user", prompt);
  byId("chat-prompt").value = "";
  const pending = appendChatMessage("assistant", "Raciocinando", true);
  const startedAt = performance.now();
  byId("chat-submit").disabled = true;
  try {
    const result = await apiRequest("/chat", { method: "POST", body: {
      pergunta: prompt,
      system_prompt: byId("system-prompt").value.trim(),
      temperatura: Number(byId("temperature").value)
    }});
    pending.classList.remove("loading");
    pending.querySelector("p").textContent = result.resposta || "Sem resposta do modelo.";
    updateExecution(result, startedAt);
  } catch (error) {
    pending.classList.remove("loading");
    pending.querySelector("p").textContent = `Erro: ${error.message}`;
    showToast(error.message, true);
  } finally { byId("chat-submit").disabled = false; }
}

function updateSummaryMode() {
  const email = byId("summary-preset").value === "email";
  byId("email-fields").hidden = !email;
  byId("summary-text-label").textContent = email ? "Corpo do e-mail" : "Conteúdo para analisar";
}

function loadSummaryPreset(fillSample = false) {
  const preset = presets[byId("summary-preset").value];
  byId("summary-instructions").value = preset.instructions;
  updateSummaryMode();
  if (fillSample) {
    byId("summary-email-subject").value = preset.subject || "";
    byId("summary-email-from").value = preset.from || "";
    byId("summary-text").value = preset.sample;
    updateSummaryCount();
  }
}

function updateSummaryCount() {
  byId("summary-count").textContent = byId("summary-text").value.length.toLocaleString("pt-BR");
}

async function submitSummary(event) {
  event.preventDefault();
  const text = byId("summary-text").value.trim();
  if (!text) return;
  const email = byId("summary-preset").value === "email";
  const output = byId("summary-output");
  const startedAt = performance.now();
  output.className = "rich-output busy";
  output.textContent = "Sintetizando o conteúdo...";
  byId("summary-submit").disabled = true;
  const body = email ? {
    assunto: byId("summary-email-subject").value.trim() || undefined,
    remetente: byId("summary-email-from").value.trim() || undefined,
    corpo: text,
    instrucoes: byId("summary-instructions").value.trim(),
    max_tokens: 800
  } : { texto: text, instrucoes: byId("summary-instructions").value.trim(), max_tokens: 800 };
  try {
    const result = await apiRequest(email ? "/summarize/email" : "/summarize", { method: "POST", body });
    output.className = "rich-output";
    output.textContent = result.resposta;
    updateExecution(result, startedAt);
  } catch (error) {
    output.className = "rich-output";
    output.textContent = `Erro: ${error.message}`;
    showToast(error.message, true);
  } finally { byId("summary-submit").disabled = false; }
}

function handleImage(file) {
  if (!file || !file.type.startsWith("image/")) { showToast("Selecione uma imagem válida.", true); return; }
  const reader = new FileReader();
  reader.onload = () => {
    const dataUrl = String(reader.result);
    state.image = { base64: dataUrl.split(",")[1], mediaType: file.type };
    byId("vision-preview").src = dataUrl;
    byId("vision-preview").hidden = false;
    byId("upload-copy").hidden = true;
    byId("vision-submit").disabled = false;
  };
  reader.readAsDataURL(file);
}

async function submitVision(event) {
  event.preventDefault();
  if (!state.image) return;
  const output = byId("vision-output");
  const startedAt = performance.now();
  output.className = "rich-output busy";
  output.textContent = "Interpretando a imagem...";
  byId("vision-submit").disabled = true;
  try {
    const result = await apiRequest("/vision", { method: "POST", body: {
      imagem_base64: state.image.base64,
      imagem_media_type: state.image.mediaType,
      prompt: byId("vision-prompt").value.trim()
    }});
    output.className = "rich-output";
    output.textContent = result.resposta;
    updateExecution(result, startedAt);
  } catch (error) {
    output.className = "rich-output";
    output.textContent = `Erro: ${error.message}`;
    showToast(error.message, true);
  } finally { byId("vision-submit").disabled = false; }
}

function openAdminDialog() {
  byId("admin-login-error").textContent = "";
  byId("admin-key").value = "";
  byId("admin-dialog").showModal();
  window.setTimeout(() => byId("admin-key").focus(), 50);
}

async function authenticateAdmin(event) {
  event.preventDefault();
  const key = byId("admin-key").value.trim();
  if (!key) return;
  state.adminKey = key;
  byId("admin-login-button").disabled = true;
  byId("admin-login-error").textContent = "Validando...";
  try {
    const config = await apiRequest("/admin/config", { admin: true });
    state.adminConfig = config;
    revealAdmin(config);
    byId("admin-dialog").close();
    navigate(state.pendingAdminView || "admin");
    showToast("Workspace administrativo desbloqueado.");
  } catch (error) {
    state.adminKey = "";
    byId("admin-login-error").textContent = error.message;
  } finally { byId("admin-login-button").disabled = false; }
}

function revealAdmin(config) {
  byId("admin-nav").hidden = false;
  byId("dw-nav").hidden = false;
  byId("admin-access-label").textContent = "Admin ativo";
  byId("overview-dw").textContent = config.dw_enabled ? "Configurado" : "Desativado";
  byId("overview-dw-copy").textContent = config.dw_enabled ? `${config.dw_host}:${config.dw_port}` : "Ative no backend/.env";
  byId("admin-environment").textContent = config.environment;
  byId("admin-provider").textContent = config.provider;
  byId("admin-chat-model").textContent = config.chat_model;
  byId("admin-vision-model").textContent = config.vision_model;
  byId("admin-timeout").textContent = `${config.request_timeout}s`;
  byId("admin-dw-host").textContent = config.dw_enabled ? `${config.dw_host}:${config.dw_port}` : "Desativado";
  byId("admin-dw-database").textContent = config.dw_database || "—";
  byId("admin-dw-user").textContent = config.dw_user || "—";
  byId("admin-dw-ssl").textContent = config.dw_sslmode || "—";
  byId("admin-dw-schemas").textContent = config.dw_allowed_schemas.join(", ") || "—";
  byId("dw-connection-label").textContent = config.dw_enabled ? "Configurado · teste pendente" : "Integração desativada";
}

function logoutAdmin() {
  state.adminKey = "";
  state.adminConfig = null;
  byId("admin-nav").hidden = true;
  byId("dw-nav").hidden = true;
  byId("admin-access-label").textContent = "Admin";
  byId("overview-dw").textContent = "Protegido";
  byId("overview-dw-copy").textContent = "Acesso administrativo";
  navigate("overview");
  showToast("Sessão administrativa encerrada.");
}

async function testWarehouse() {
  const buttons = [byId("test-dw")];
  buttons.forEach((button) => { button.disabled = true; });
  byId("admin-dw-dot").className = "live-dot waiting";
  byId("dw-connection-dot").className = "live-dot waiting";
  try {
    const result = await apiRequest("/admin/dw/test", { method: "POST", admin: true });
    byId("admin-dw-dot").className = "live-dot";
    byId("dw-connection-dot").className = "live-dot";
    byId("dw-connection-label").textContent = `${result.database} · somente leitura`;
    showToast(`DW conectado como ${result.user}.`);
  } catch (error) {
    byId("admin-dw-dot").className = "live-dot offline";
    byId("dw-connection-dot").className = "live-dot offline";
    byId("dw-connection-label").textContent = "Falha de conexão";
    showToast(error.message, true);
  } finally { buttons.forEach((button) => { button.disabled = false; }); }
}

async function loadWarehouseSchema(force = false) {
  const buttons = [byId("load-schema"), byId("refresh-schema")];
  buttons.forEach((button) => { button.disabled = true; });
  try {
    const schema = await apiRequest(`/admin/dw/schema?refresh=${force}`, { admin: true });
    renderSchema(schema.tables);
    byId("dw-table-count").textContent = `${schema.tables.length} tabelas`;
    byId("dw-connection-label").textContent = `${schema.database} · ${schema.user}`;
    byId("dw-connection-dot").className = "live-dot";
    showToast(`${schema.tables.length} tabelas fact/dim carregadas.`);
  } catch (error) {
    byId("schema-list").textContent = error.message;
    byId("dw-connection-dot").className = "live-dot offline";
    showToast(error.message, true);
  } finally { buttons.forEach((button) => { button.disabled = false; }); }
}

function renderSchema(tables) {
  const container = byId("schema-list");
  container.replaceChildren();
  if (!tables.length) { const empty = document.createElement("p"); empty.textContent = "Nenhuma tabela permitida encontrada."; container.appendChild(empty); return; }
  tables.forEach((table) => {
    const item = document.createElement("div");
    item.className = "schema-table";
    const name = document.createElement("strong");
    name.textContent = `${table.schema_name}.${table.table_name}`;
    const columns = document.createElement("span");
    columns.textContent = table.columns.map((column) => column.name).join(" · ");
    item.append(name, columns);
    container.appendChild(item);
  });
}

async function submitWarehouseQuestion(event) {
  event.preventDefault();
  const question = byId("dw-question").value.trim();
  if (!question) return;
  const resultSection = byId("dw-result");
  resultSection.hidden = false;
  byId("dw-answer").className = "rich-output busy";
  byId("dw-answer").textContent = "Aethra está lendo o schema, construindo e validando a consulta...";
  byId("dw-sql").textContent = "-- aguardando SQL seguro";
  byId("dw-table").replaceChildren();
  byId("dw-submit").disabled = true;
  const startedAt = performance.now();
  try {
    const result = await apiRequest("/dw/ask", { method: "POST", admin: true, body: { pergunta: question } });
    byId("dw-answer").className = "rich-output";
    byId("dw-answer").textContent = result.resposta;
    byId("dw-sql").textContent = result.sql;
    byId("dw-row-count").textContent = `${result.row_count} linhas${result.truncated ? " · limitado" : ""}`;
    renderDataTable(result.columns, result.rows);
    updateExecution(result, startedAt);
  } catch (error) {
    byId("dw-answer").className = "rich-output";
    byId("dw-answer").textContent = `Não foi possível concluir: ${error.message}`;
    showToast(error.message, true);
  } finally { byId("dw-submit").disabled = false; }
}

function renderDataTable(columns, rows) {
  const wrapper = byId("dw-table");
  wrapper.replaceChildren();
  if (!rows.length) { const empty = document.createElement("div"); empty.className = "rich-output"; empty.textContent = "A consulta não retornou linhas."; wrapper.appendChild(empty); return; }
  const table = document.createElement("table");
  table.className = "data-table";
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((column) => { const th = document.createElement("th"); th.textContent = column; headRow.appendChild(th); });
  head.appendChild(headRow);
  const body = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    row.forEach((value) => { const td = document.createElement("td"); td.textContent = value === null ? "NULL" : String(value); td.title = td.textContent; tr.appendChild(td); });
    body.appendChild(tr);
  });
  table.append(head, body);
  wrapper.appendChild(table);
}

async function copyElement(id) {
  try { await navigator.clipboard.writeText(byId(id).innerText); showToast("Conteúdo copiado."); }
  catch (_error) { showToast("Não foi possível copiar.", true); }
}

function updateIntegrationCode() {
  byId("docs-base-url").textContent = apiUrl();
  byId("integration-code").textContent = `$headers = @{ "X-Admin-Key" = "SUA_CHAVE_ADMIN" }
$body = @{ pergunta = "Qual foi a receita mensal por região?" } | ConvertTo-Json

Invoke-RestMethod \`
  -Uri "${apiUrl()}/dw/ask" \`
  -Method Post \`
  -Headers $headers \`
  -ContentType "application/json; charset=utf-8" \`
  -Body ([Text.Encoding]::UTF8.GetBytes($body))`;
}

function setupEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.view)));
  document.querySelectorAll("[data-open-view]").forEach((button) => button.addEventListener("click", () => {
    navigate(button.dataset.openView);
    if (button.dataset.chatSample) byId("chat-prompt").value = button.dataset.chatSample;
  }));
  [byId("hero-dw-button"), byId("quick-dw")].forEach((button) => button.addEventListener("click", () => navigate("warehouse")));
  byId("refresh-status").addEventListener("click", checkHealth);

  byId("chat-form").addEventListener("submit", submitChat);
  byId("chat-prompt").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); byId("chat-form").requestSubmit(); } });
  byId("temperature").addEventListener("input", (event) => { byId("temperature-value").textContent = event.target.value; });
  byId("clear-chat").addEventListener("click", () => { byId("chat-messages").replaceChildren(); appendChatMessage("assistant", "Conversa limpa. Em que vamos trabalhar?"); });

  byId("summary-preset").addEventListener("change", () => loadSummaryPreset(false));
  byId("load-sample").addEventListener("click", () => loadSummaryPreset(true));
  byId("summary-text").addEventListener("input", updateSummaryCount);
  byId("summary-form").addEventListener("submit", submitSummary);

  byId("vision-file").addEventListener("change", (event) => handleImage(event.target.files[0]));
  const dropZone = byId("drop-zone");
  ["dragenter", "dragover"].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.remove("dragging"); }));
  dropZone.addEventListener("drop", (event) => handleImage(event.dataTransfer.files[0]));
  byId("vision-form").addEventListener("submit", submitVision);

  byId("admin-access").addEventListener("click", () => state.adminKey ? navigate("admin") : openAdminDialog());
  byId("admin-login-form").addEventListener("submit", authenticateAdmin);
  byId("close-admin-dialog").addEventListener("click", () => byId("admin-dialog").close());
  byId("admin-logout").addEventListener("click", logoutAdmin);
  byId("test-dw").addEventListener("click", testWarehouse);
  byId("load-schema").addEventListener("click", () => loadWarehouseSchema(true));
  byId("refresh-schema").addEventListener("click", () => loadWarehouseSchema(true));
  byId("dw-form").addEventListener("submit", submitWarehouseQuestion);
  document.querySelectorAll("[data-dw-sample]").forEach((button) => button.addEventListener("click", () => { byId("dw-question").value = button.dataset.dwSample; }));

  byId("save-connection").addEventListener("click", () => { sessionStorage.setItem("aethra.apiUrl", apiUrl()); updateIntegrationCode(); checkHealth(); showToast("Endpoint atualizado nesta sessão."); });
  byId("api-url").addEventListener("input", updateIntegrationCode);
  document.querySelectorAll("[data-copy]").forEach((button) => button.addEventListener("click", () => copyElement(button.dataset.copy)));
}

document.addEventListener("DOMContentLoaded", () => {
  byId("api-url").value = sessionStorage.getItem("aethra.apiUrl") || resolveDefaultApiUrl();
  setupEvents();
  updateSummaryMode();
  updateSummaryCount();
  updateIntegrationCode();
  checkHealth();
});
