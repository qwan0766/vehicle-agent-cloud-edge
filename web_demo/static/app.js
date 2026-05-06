const state = {
  network: "ONLINE",
  scenarios: [],
  demoSteps: [],
  users: [],
  userId: "user_001",
  activeDemoId: "",
  requestSeq: 0,
  activeRequestId: 0,
};

const nodes = {
  networkBadge: document.querySelector("#networkBadge"),
  safetyBadge: document.querySelector("#safetyBadge"),
  gpsValue: document.querySelector("#gpsValue"),
  speedValue: document.querySelector("#speedValue"),
  batteryValue: document.querySelector("#batteryValue"),
  batteryBar: document.querySelector("#batteryBar"),
  onlineBtn: document.querySelector("#onlineBtn"),
  offlineBtn: document.querySelector("#offlineBtn"),
  userIdValue: document.querySelector("#userIdValue"),
  userSelect: document.querySelector("#userSelect"),
  scenarioButtons: document.querySelector("#scenarioButtons"),
  commandInput: document.querySelector("#commandInput"),
  runBtn: document.querySelector("#runBtn"),
  commandError: document.querySelector("#commandError"),
  demoStepCount: document.querySelector("#demoStepCount"),
  demoSteps: document.querySelector("#demoSteps"),
  demoFocus: document.querySelector("#demoFocus"),
  demoTalkTrack: document.querySelector("#demoTalkTrack"),
  demoExpectedPanels: document.querySelector("#demoExpectedPanels"),
  traceMode: document.querySelector("#traceMode"),
  graphMode: document.querySelector("#graphMode"),
  graphPath: document.querySelector("#graphPath"),
  agentTrace: document.querySelector("#agentTrace"),
  runtimeTrace: document.querySelector("#runtimeTrace"),
  ragCount: document.querySelector("#ragCount"),
  ragContext: document.querySelector("#ragContext"),
  feedbackStatus: document.querySelector("#feedbackStatus"),
  feedbackEvent: document.querySelector("#feedbackEvent"),
  feedbackPreference: document.querySelector("#feedbackPreference"),
  localContextWindow: document.querySelector("#localContextWindow"),
  localContextProvider: document.querySelector("#localContextProvider"),
  localContextModel: document.querySelector("#localContextModel"),
  localContextSummary: document.querySelector("#localContextSummary"),
  localContextRecent: document.querySelector("#localContextRecent"),
  localContextPrompt: document.querySelector("#localContextPrompt"),
  evalTotal: document.querySelector("#evalTotal"),
  evalIntent: document.querySelector("#evalIntent"),
  evalSafety: document.querySelector("#evalSafety"),
  evalRag: document.querySelector("#evalRag"),
  acceptanceRefreshBtn: document.querySelector("#acceptanceRefreshBtn"),
  acceptanceStatus: document.querySelector("#acceptanceStatus"),
  acceptanceTime: document.querySelector("#acceptanceTime"),
  acceptanceSteps: document.querySelector("#acceptanceSteps"),
  smokeBtn: document.querySelector("#smokeBtn"),
  providerLlm: document.querySelector("#providerLlm"),
  providerLocalLlm: document.querySelector("#providerLocalLlm"),
  providerOrchestrator: document.querySelector("#providerOrchestrator"),
  providerMap: document.querySelector("#providerMap"),
  providerWeather: document.querySelector("#providerWeather"),
  providerCharge: document.querySelector("#providerCharge"),
  smokeResults: document.querySelector("#smokeResults"),
  routeProvider: document.querySelector("#routeProvider"),
  routeDistance: document.querySelector("#routeDistance"),
  routeDuration: document.querySelector("#routeDuration"),
  routeStrategy: document.querySelector("#routeStrategy"),
  chargeStations: document.querySelector("#chargeStations"),
  requestIdValue: document.querySelector("#requestIdValue"),
  commandTypeValue: document.querySelector("#commandTypeValue"),
  safetyValue: document.querySelector("#safetyValue"),
  executionValue: document.querySelector("#executionValue"),
  resultOutput: document.querySelector("#resultOutput"),
};

async function init() {
  try {
    const response = await fetch("/api/state");
    const payload = await parseJsonResponse(response);
    state.scenarios = payload.scenarios;
    state.demoSteps = payload.demo_steps || [];
    state.users = payload.users;
    renderVehicle(payload.vehicle_state);
    renderOfflineEvaluation(payload.offline_evaluation);
    renderAcceptance(payload.acceptance);
    renderProviders(payload.providers);
    renderUsers();
    renderScenarioButtons();
    renderDemoSteps();
    bindEvents();
  } catch (error) {
    nodes.resultOutput.textContent = `页面初始化失败：${error.message}`;
  }
}

function renderDemoSteps() {
  nodes.demoSteps.innerHTML = "";
  nodes.demoStepCount.textContent = `${state.demoSteps.length} steps`;
  if (!state.demoSteps.length) {
    nodes.demoSteps.textContent = "暂无演示步骤";
    return;
  }

  state.demoSteps.forEach((step) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "demo-step";
    button.dataset.demoId = step.id;

    const title = document.createElement("strong");
    title.textContent = step.title;
    const meta = document.createElement("span");
    meta.textContent = `${step.network} · ${step.content}`;
    button.append(title, meta);
    button.addEventListener("click", () => activateDemoStep(step, true));
    nodes.demoSteps.appendChild(button);
  });

  activateDemoStep(state.demoSteps[0], false);
}

function activateDemoStep(step, shouldRun) {
  state.activeDemoId = step.id;
  nodes.commandInput.value = step.content;
  setNetwork(step.network);
  renderDemoNotes(step);
  document.querySelectorAll(".demo-step").forEach((button) => {
    button.classList.toggle("active", button.dataset.demoId === step.id);
  });
  if (shouldRun) {
    runCommand();
  }
}

function renderDemoNotes(step) {
  nodes.demoFocus.textContent = step.focus;
  nodes.demoTalkTrack.textContent = step.talk_track;
  nodes.demoExpectedPanels.innerHTML = "";
  (step.expected_panels || []).forEach((panel) => {
    const tag = document.createElement("span");
    tag.textContent = panel;
    nodes.demoExpectedPanels.appendChild(tag);
  });
}

function renderOfflineEvaluation(report) {
  nodes.evalTotal.textContent = `${report.total} cases`;
  nodes.evalIntent.textContent = formatPercent(report.intent_accuracy);
  nodes.evalSafety.textContent = formatPercent(report.safety_block_recall);
  nodes.evalRag.textContent = formatPercent(report.rag_hit_rate);
}

function formatPercent(value) {
  return `${Math.round(Number(value) * 100)}%`;
}

function bindEvents() {
  nodes.onlineBtn.addEventListener("click", () => setNetwork("ONLINE"));
  nodes.offlineBtn.addEventListener("click", () => setNetwork("OFFLINE"));
  nodes.runBtn.addEventListener("click", runCommand);
  nodes.smokeBtn.addEventListener("click", runSmokeTest);
  nodes.acceptanceRefreshBtn.addEventListener("click", refreshAcceptance);
  nodes.userSelect.addEventListener("change", () => {
    state.userId = nodes.userSelect.value;
    nodes.userIdValue.textContent = state.userId;
  });
  nodes.commandInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      runCommand();
    }
  });
}

async function refreshAcceptance() {
  nodes.acceptanceRefreshBtn.disabled = true;
  nodes.acceptanceRefreshBtn.textContent = "读取中";
  try {
    const response = await fetch("/api/acceptance");
    const payload = await parseJsonResponse(response);
    renderAcceptance(payload);
  } catch (error) {
    nodes.acceptanceStatus.textContent = "ERROR";
    nodes.acceptanceStatus.className = "status-danger";
    nodes.acceptanceSteps.textContent = `验收报告读取失败：${error.message}`;
  } finally {
    nodes.acceptanceRefreshBtn.disabled = false;
    nodes.acceptanceRefreshBtn.textContent = "刷新";
  }
}

function renderAcceptance(report) {
  const payload = report || {};
  nodes.acceptanceStatus.textContent = payload.overall_status || "UNKNOWN";
  nodes.acceptanceStatus.className =
    payload.overall_status === "PASS" ? "status-pass" : "status-danger";
  nodes.acceptanceTime.textContent = payload.generated_at || "-";
  nodes.acceptanceSteps.innerHTML = "";

  if (!payload.available) {
    nodes.acceptanceSteps.textContent = "尚未生成验收报告";
    return;
  }

  const steps = payload.steps || [];
  if (!steps.length) {
    nodes.acceptanceSteps.textContent = "报告中没有验收步骤摘要";
    return;
  }

  steps.forEach((step) => {
    const row = document.createElement("article");
    row.className = `acceptance-row ${step.status.toLowerCase()}`;
    const name = document.createElement("strong");
    name.textContent = step.name;
    const meta = document.createElement("span");
    meta.textContent = `${step.status} · ${step.duration}`;
    row.append(name, meta);
    nodes.acceptanceSteps.appendChild(row);
  });
}

function renderProviders(providers) {
  nodes.providerLlm.textContent = providers.llm;
  nodes.providerLocalLlm.textContent = providers.local_llm || "-";
  nodes.providerOrchestrator.textContent = providers.orchestrator || "-";
  nodes.providerMap.textContent = providers.map;
  nodes.providerWeather.textContent = providers.weather;
  nodes.providerCharge.textContent = providers.charge;
}

async function runSmokeTest() {
  nodes.smokeBtn.disabled = true;
  nodes.smokeBtn.textContent = "检测中";
  nodes.smokeResults.textContent = "正在调用真实接口";
  try {
    const response = await fetch("/api/provider-smoke", { method: "POST" });
    const payload = await parseJsonResponse(response);
    renderSmokeResults(payload.results || []);
  } catch (error) {
    nodes.smokeResults.textContent = `接口检测失败：${error.message}`;
  } finally {
    nodes.smokeBtn.disabled = false;
    nodes.smokeBtn.textContent = "Smoke Test";
  }
}

function renderSmokeResults(results) {
  nodes.smokeResults.innerHTML = "";
  results.forEach((item) => {
    const row = document.createElement("article");
    row.className = `smoke-row ${item.status.toLowerCase()}`;
    const name = document.createElement("strong");
    name.textContent = item.name;
    const status = document.createElement("span");
    status.textContent = item.status;
    row.append(name, status);
    nodes.smokeResults.appendChild(row);
  });
}

function renderUsers() {
  nodes.userSelect.innerHTML = "";
  state.users.forEach((user) => {
    const option = document.createElement("option");
    option.value = user.user_id;
    option.textContent = user.label;
    nodes.userSelect.appendChild(option);
  });
  nodes.userSelect.value = state.userId;
  nodes.userIdValue.textContent = state.userId;
}

function setNetwork(network) {
  state.network = network;
  nodes.onlineBtn.classList.toggle("active", network === "ONLINE");
  nodes.offlineBtn.classList.toggle("active", network === "OFFLINE");
  nodes.networkBadge.textContent = network;
}

function renderScenarioButtons() {
  nodes.scenarioButtons.innerHTML = "";
  state.scenarios.forEach((scenario) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = scenario.label;
    button.addEventListener("click", () => {
      nodes.commandInput.value = scenario.content;
      setNetwork(scenario.network);
      runCommand();
    });
    nodes.scenarioButtons.appendChild(button);
  });
}

async function runCommand() {
  const content = nodes.commandInput.value.trim();
  if (!content) {
    return;
  }
  const requestId = state.requestSeq + 1;
  state.requestSeq = requestId;
  state.activeRequestId = requestId;
  const userId = state.userId;
  const network = state.network;

  nodes.runBtn.disabled = true;
  nodes.runBtn.textContent = "运行中";
  nodes.resultOutput.textContent = "正在调度 Agent";
  clearCommandError();
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        user_id: userId,
        network,
      }),
    });
    const payload = await parseJsonResponse(response);
    if (requestId !== state.activeRequestId) {
      return;
    }
    renderVehicle(payload.vehicle_state);
    renderResult(payload);
  } catch (error) {
    if (requestId !== state.activeRequestId) {
      return;
    }
    renderCommandError(error);
  } finally {
    if (requestId === state.activeRequestId) {
      nodes.runBtn.disabled = false;
      nodes.runBtn.textContent = "运行指令";
    }
  }
}

function clearCommandError() {
  nodes.commandError.hidden = true;
  nodes.commandError.textContent = "";
}

function renderCommandError(error) {
  const info = error.info || {};
  const title = info.user_title || "在线调用失败";
  const message = info.user_message || error.message;
  const html = errorInfoToHtml(title, message, info);
  nodes.commandError.hidden = false;
  nodes.commandError.innerHTML = html;
  nodes.resultOutput.innerHTML = html;
  nodes.traceMode.textContent = title;
  nodes.safetyBadge.textContent = "调用失败";
  nodes.safetyBadge.classList.remove("badge-safe");
  nodes.safetyBadge.classList.add("badge-danger");
  nodes.agentTrace.innerHTML = "";
  ["LocalIntentAgent", "GlobalSafetyDispatchAgent", "ProviderError"].forEach((agent) => {
    const item = document.createElement("li");
    item.textContent = agent;
    item.className = agent === "ProviderError" ? "blocked" : "";
    nodes.agentTrace.appendChild(item);
  });
  nodes.runtimeTrace.innerHTML = html;
  nodes.ragCount.textContent = "0 条";
  nodes.ragContext.textContent = "本次在线调用失败，没有可展示的新召回结果";
  renderGraphPath({});
  renderLocalContext({});
  renderRouteSummary({}, []);
}

function errorInfoToHtml(title, message, info) {
  const suggestions = Array.isArray(info.suggestions) ? info.suggestions : [];
  const technical = info.technical_message || info.message || "";
  const suggestionHtml = suggestions.length
    ? `<ul>${suggestions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "";
  const technicalHtml = technical
    ? `<small>技术细节：${escapeHtml(technical)}</small>`
    : "";
  return (
    `<strong>${escapeHtml(title)}</strong>` +
    `<p>${escapeHtml(message)}</p>` +
    suggestionHtml +
    technicalHtml
  );
}

async function parseJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    const errorInfo = payload.error || {};
    const message = errorInfo.user_message || errorInfo.message || `HTTP ${response.status}`;
    const error = new Error(message);
    error.info = errorInfo;
    throw error;
  }
  return payload;
}

function renderVehicle(vehicle) {
  nodes.gpsValue.textContent = vehicle.gps;
  nodes.speedValue.textContent = vehicle.speed_kmh;
  nodes.batteryValue.textContent = vehicle.battery_percent;
  nodes.batteryBar.style.width = `${vehicle.battery_percent}%`;
  nodes.networkBadge.textContent = vehicle.network;
  state.network = vehicle.network;
  nodes.onlineBtn.classList.toggle("active", vehicle.network === "ONLINE");
  nodes.offlineBtn.classList.toggle("active", vehicle.network === "OFFLINE");
}

function renderResult(payload) {
  const { request, result, agent_trace: agentTrace } = payload;
  nodes.requestIdValue.textContent = request.request_id;
  nodes.commandTypeValue.textContent = request.command_type;
  nodes.safetyValue.textContent = request.safety;
  nodes.executionValue.textContent = result.status;
  renderMarkdown(nodes.resultOutput, result.output);
  nodes.traceMode.textContent =
    result.status === "BLOCKED"
      ? "安全拦截"
      : request.network === "ONLINE"
      ? "端云协同"
      : "本地兜底";

  if (result.status === "BLOCKED") {
    nodes.safetyBadge.textContent =
      request.safety === "DANGEROUS" ? "危险拦截" : "策略拦截";
  } else {
    nodes.safetyBadge.textContent = "安全正常";
  }
  nodes.safetyBadge.classList.toggle("badge-danger", result.status === "BLOCKED");
  nodes.safetyBadge.classList.toggle("badge-safe", result.status !== "BLOCKED");

  nodes.agentTrace.innerHTML = "";
  agentTrace.forEach((agent) => {
    const item = document.createElement("li");
    item.textContent = agent;
    item.className = agentClass(agent);
    nodes.agentTrace.appendChild(item);
  });

  renderRuntimeTrace(payload.runtime_trace || [], result.status);
  renderGraphPath(payload.graph || {});
  renderRouteSummary(payload.route_summary || {}, payload.charge_stations || []);
  renderRagContext(payload.rag_context || []);
  renderFeedback(payload.feedback || {});
  renderLocalContext(payload.local_context || {});
}

function renderRouteSummary(route, stations) {
  nodes.routeProvider.textContent = route.destination_name
    ? `${route.provider} -> ${route.destination_name}`
    : route.provider || "无路线";
  nodes.routeDistance.textContent = route.distance_km !== undefined ? `${route.distance_km} km` : "-";
  nodes.routeDuration.textContent = route.duration_minutes !== undefined ? `${route.duration_minutes} 分钟` : "-";
  nodes.routeStrategy.textContent = route.strategy || "-";
  nodes.chargeStations.innerHTML = "";
  if (!stations.length) {
    nodes.chargeStations.textContent = "当前链路未查询充电站";
    return;
  }
  stations.forEach((station) => {
    const row = document.createElement("article");
    row.className = "station-row";
    const name = document.createElement("strong");
    name.textContent = station.name;
    const meta = document.createElement("span");
    meta.textContent = `${station.distance_km} km | ${station.status}`;
    row.append(name, meta);
    nodes.chargeStations.appendChild(row);
  });
}

function renderRuntimeTrace(items, status = "") {
  nodes.runtimeTrace.innerHTML = "";
  if (!items.length) {
    nodes.runtimeTrace.textContent =
      status === "BLOCKED" ? "拦截结果未调用云端工具" : "本地链路未调用云端工具";
    return;
  }

  items.forEach((item) => {
    const row = document.createElement("article");
    row.className = "tool-call";

    const header = document.createElement("header");
    const name = document.createElement("strong");
    name.textContent = item.tool_name;
    const duration = document.createElement("span");
    duration.textContent = `${item.duration_ms} ms`;
    header.append(name, duration);

    const output = document.createElement("small");
    output.textContent = typeof item.output === "string" ? item.output : JSON.stringify(item.output);

    row.append(header, output);
    nodes.runtimeTrace.appendChild(row);
  });
}

function renderGraphPath(graph) {
  const payload = graph || {};
  const path = Array.isArray(payload.path) ? payload.path : [];
  const mode = payload.mode || "not_run";
  const fallbackText = payload.fallback ? " · fallback" : "";
  nodes.graphMode.textContent = `${mode}${fallbackText}`;
  nodes.graphPath.textContent = path.length ? path.join(" -> ") : "未执行云端图";
}

function renderFeedback(feedback) {
  nodes.feedbackStatus.textContent = feedback.event_status || "未记录";
  nodes.feedbackEvent.textContent = feedback.event_log || "-";
  nodes.feedbackPreference.textContent = feedback.preference_update || "-";
}

function renderLocalContext(context) {
  const payload = context || {};
  const recentTurns = Array.isArray(payload.recent_turns) ? payload.recent_turns : [];
  const totalTurns = Number(payload.total_turns || 0);
  const compressedTurns = Number(payload.compressed_turns || 0);
  const localLlm = payload.local_llm || {};
  const windowInfo = payload.window || {};
  const estimatedTokens = windowInfo.estimated_prompt_tokens || 0;
  const promptBudgetTokens = windowInfo.prompt_budget_tokens || 0;
  const maxOutputTokens = windowInfo.max_output_tokens || 0;
  const budgetStatus = windowInfo.over_budget ? "over budget" : "within budget";

  nodes.localContextWindow.textContent = totalTurns
    ? `${payload.agent_id || "local_intent"} · ${totalTurns} turns / ${compressedTurns} compressed · ~${estimatedTokens}/${promptBudgetTokens} prompt tokens · max ${maxOutputTokens} output · ${budgetStatus}`
    : "等待本地记忆";
  nodes.localContextProvider.textContent = localLlm.provider || "-";
  nodes.localContextModel.textContent = localLlm.model || "-";
  nodes.localContextSummary.textContent = payload.summary || "暂无压缩摘要";
  nodes.localContextPrompt.textContent = localLlm.prompt_preview || "暂无 prompt 预览";
  nodes.localContextRecent.innerHTML = "";

  if (!recentTurns.length) {
    nodes.localContextRecent.textContent = "暂无最近交互";
    return;
  }

  recentTurns.slice(-4).forEach((turn) => {
    const row = document.createElement("article");
    row.className = "context-turn";

    const input = document.createElement("strong");
    input.textContent = turn.user_input || "-";
    const meta = document.createElement("span");
    meta.textContent = `${turn.command_type || "-"} · ${turn.network || "-"} · ${turn.execution_status || "-"}`;

    row.append(input, meta);
    nodes.localContextRecent.appendChild(row);
  });
}

function renderMarkdown(target, markdown) {
  target.innerHTML = markdownToHtml(markdown || "");
}

function markdownToHtml(markdown) {
  const lines = String(markdown).replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let listType = "";
  let inCodeBlock = false;
  let codeLines = [];

  function closeList() {
    if (listType) {
      html.push(`</${listType}>`);
      listType = "";
    }
  }

  function openList(type) {
    if (listType !== type) {
      closeList();
      listType = type;
      html.push(`<${type}>`);
    }
  }

  lines.forEach((line) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      if (inCodeBlock) {
        html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines = [];
      } else {
        closeList();
      }
      inCodeBlock = !inCodeBlock;
      return;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      return;
    }

    if (!trimmed) {
      closeList();
      return;
    }

    if (trimmed.startsWith("### ")) {
      closeList();
      html.push(`<h4>${formatInline(trimmed.slice(4))}</h4>`);
      return;
    }

    if (trimmed.startsWith("## ")) {
      closeList();
      html.push(`<h3>${formatInline(trimmed.slice(3))}</h3>`);
      return;
    }

    if (trimmed.startsWith("# ")) {
      closeList();
      html.push(`<h3>${formatInline(trimmed.slice(2))}</h3>`);
      return;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      openList("ul");
      html.push(`<li>${formatInline(trimmed.replace(/^[-*]\s+/, ""))}</li>`);
      return;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      openList("ol");
      html.push(`<li>${formatInline(trimmed.replace(/^\d+\.\s+/, ""))}</li>`);
      return;
    }

    closeList();
    html.push(`<p>${formatInline(trimmed)}</p>`);
  });

  closeList();
  if (inCodeBlock) {
    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }
  return html.join("");
}

function formatInline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderRagContext(items) {
  nodes.ragCount.textContent = `${items.length} 条`;
  nodes.ragContext.innerHTML = "";

  if (!items.length) {
    nodes.ragContext.textContent = "没有召回相关知识";
    return;
  }

  items.forEach((item) => {
    const doc = document.createElement("article");
    doc.className = "rag-doc";

    const header = document.createElement("header");
    const stage = document.createElement("span");
    stage.textContent = item.stage;
    const score = document.createElement("span");
    score.textContent = `score ${item.score}`;
    header.append(stage, score);

    const text = document.createElement("strong");
    text.textContent = item.text;

    const keywords = document.createElement("small");
    keywords.textContent = item.matched_keywords.length
      ? `命中关键词：${item.matched_keywords.join("、")}`
      : `文档ID：${item.doc_id}`;

    doc.append(header, text, keywords);
    nodes.ragContext.appendChild(doc);
  });
}

function agentClass(agent) {
  if (
    agent.includes("Cloud") ||
    agent.includes("GlobalDispatch") ||
    agent.includes("TripPlanning") ||
    agent.includes("UserProfile") ||
    agent.includes("VectorKnowledge") ||
    agent.includes("ExternalEcology")
  ) {
    return "cloud";
  }
  if (
    agent.includes("Fallback") ||
    agent.includes("CabinVehicleControl") ||
    agent.includes("DataUpload")
  ) {
    return "local";
  }
  if (agent.includes("Block")) {
    return "blocked";
  }
  return "";
}

init();
