const state = {
  network: "ONLINE",
  scenarios: [],
  users: [],
  userId: "user_001",
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
  traceMode: document.querySelector("#traceMode"),
  agentTrace: document.querySelector("#agentTrace"),
  runtimeTrace: document.querySelector("#runtimeTrace"),
  ragCount: document.querySelector("#ragCount"),
  ragContext: document.querySelector("#ragContext"),
  feedbackStatus: document.querySelector("#feedbackStatus"),
  feedbackEvent: document.querySelector("#feedbackEvent"),
  feedbackPreference: document.querySelector("#feedbackPreference"),
  requestIdValue: document.querySelector("#requestIdValue"),
  commandTypeValue: document.querySelector("#commandTypeValue"),
  safetyValue: document.querySelector("#safetyValue"),
  executionValue: document.querySelector("#executionValue"),
  resultOutput: document.querySelector("#resultOutput"),
};

async function init() {
  const response = await fetch("/api/state");
  const payload = await response.json();
  state.scenarios = payload.scenarios;
  state.users = payload.users;
  renderVehicle(payload.vehicle_state);
  renderUsers();
  renderScenarioButtons();
  bindEvents();
  await runCommand();
}

function bindEvents() {
  nodes.onlineBtn.addEventListener("click", () => setNetwork("ONLINE"));
  nodes.offlineBtn.addEventListener("click", () => setNetwork("OFFLINE"));
  nodes.runBtn.addEventListener("click", runCommand);
  nodes.userSelect.addEventListener("change", () => {
    state.userId = nodes.userSelect.value;
    nodes.userIdValue.textContent = state.userId;
    runCommand();
  });
  nodes.commandInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      runCommand();
    }
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

  nodes.runBtn.disabled = true;
  nodes.runBtn.textContent = "运行中";
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        user_id: state.userId,
        network: state.network,
      }),
    });
    const payload = await response.json();
    renderVehicle(payload.vehicle_state);
    renderResult(payload);
  } finally {
    nodes.runBtn.disabled = false;
    nodes.runBtn.textContent = "运行指令";
  }
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
  nodes.resultOutput.textContent = result.output;
  nodes.traceMode.textContent = request.network === "ONLINE" ? "端云协同" : "本地兜底";

  nodes.safetyBadge.textContent = request.safety === "DANGEROUS" ? "危险拦截" : "安全正常";
  nodes.safetyBadge.classList.toggle("badge-danger", request.safety === "DANGEROUS");
  nodes.safetyBadge.classList.toggle("badge-safe", request.safety !== "DANGEROUS");

  nodes.agentTrace.innerHTML = "";
  agentTrace.forEach((agent) => {
    const item = document.createElement("li");
    item.textContent = agent;
    item.className = agentClass(agent);
    nodes.agentTrace.appendChild(item);
  });

  renderRuntimeTrace(payload.runtime_trace || []);
  renderRagContext(payload.rag_context || []);
  renderFeedback(payload.feedback || {});
}

function renderRuntimeTrace(items) {
  nodes.runtimeTrace.innerHTML = "";
  if (!items.length) {
    nodes.runtimeTrace.textContent = "本地链路未调用云端工具";
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

function renderFeedback(feedback) {
  nodes.feedbackStatus.textContent = feedback.event_status || "未记录";
  nodes.feedbackEvent.textContent = feedback.event_log || "-";
  nodes.feedbackPreference.textContent = feedback.preference_update || "-";
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
  if (agent.includes("Cloud")) {
    return "cloud";
  }
  if (agent.includes("Fallback") || agent === "CarControlAgent" || agent === "NavAgent") {
    return "local";
  }
  if (agent.includes("Block")) {
    return "blocked";
  }
  return "";
}

init();
