import { escapeHtml } from "../markdown.js?v=agent-trace-aligned-20260510";

export function renderVehicle(nodes, vehicle, options = {}, state = null) {
  const syncControls = options.syncControls !== false;
  const syncNetwork = options.syncNetwork !== false;
  nodes.gpsValue.textContent = vehicle.gps;
  nodes.speedValue.textContent = vehicle.speed_kmh;
  nodes.batteryValue.textContent = vehicle.battery_percent;
  nodes.batteryBar.style.width = `${vehicle.battery_percent}%`;
  nodes.roadTypeValue.textContent = vehicle.road_type || "UNKNOWN";
  nodes.speedLimitValue.textContent = vehicle.speed_limit_kmh
    ? `${vehicle.speed_limit_kmh} km/h`
    : "-";
  nodes.assistModeValue.textContent = vehicle.driver_assist_mode || "-";
  renderSafetyBadge(nodes, vehicle.safety_state || "正常");
  if (syncControls) {
    nodes.roadTypeInput.value = vehicle.road_type || "UNKNOWN";
    nodes.speedLimitInput.value = vehicle.speed_limit_kmh || 0;
    nodes.vehicleSpeedInput.value = vehicle.speed_kmh || 0;
    nodes.batteryInput.value = vehicle.battery_percent || 0;
    nodes.assistModeInput.value = vehicle.driver_assist_mode || "MANUAL";
  }
  if (syncNetwork) {
    nodes.networkBadge.textContent = vehicle.network;
    if (state) {
      state.network = vehicle.network;
    }
    nodes.onlineBtn.classList.toggle("active", vehicle.network === "ONLINE");
    nodes.offlineBtn.classList.toggle("active", vehicle.network === "OFFLINE");
  }
}

function renderSafetyBadge(nodes, safetyState) {
  nodes.safetyBadge.textContent = safetyState === "正常" ? "安全正常" : safetyState;
  nodes.safetyBadge.classList.toggle("badge-safe", safetyState === "正常");
  nodes.safetyBadge.classList.toggle("badge-danger", safetyState === "严重低电量");
  nodes.safetyBadge.classList.toggle(
    "badge-clarification",
    safetyState !== "正常" && safetyState !== "严重低电量"
  );
}

export function renderAutoEvents(nodes, events, rules) {
  nodes.autoEvents.innerHTML = "";
  const eventList = Array.isArray(events) ? events : [];
  if (eventList.length) {
    eventList.forEach((event) => {
      const item = document.createElement("article");
      item.className = `auto-event active ${String(event.severity || "INFO").toLowerCase()}`;
      item.innerHTML =
        `<strong>自动触发：${escapeHtml(event.type || "STATE_EVENT")} · ${escapeHtml(event.severity || "INFO")}</strong>` +
        `<span>${escapeHtml(event.reason || event.content || "")}</span>` +
        `<span>${escapeHtml(event.recommended_action || "")}</span>`;
      nodes.autoEvents.appendChild(item);
    });
    return;
  }
  const rule = Array.isArray(rules) && rules.length ? rules[0] : null;
  const item = document.createElement("article");
  item.className = "auto-event";
  item.innerHTML =
    "<strong>当前无自动触发</strong>" +
    `<span>${escapeHtml(rule ? rule.description : "低电量等车辆状态事件会由系统监控触发。")}</span>`;
  nodes.autoEvents.appendChild(item);
}

export function renderOfflineEvaluation(nodes, report) {
  if (!report || report.status === "PENDING") {
    nodes.evalTotal.textContent = "pending";
    nodes.evalIntent.textContent = "-";
    nodes.evalSafety.textContent = "-";
    nodes.evalRag.textContent = "-";
    return;
  }
  if (report.status === "ERROR") {
    nodes.evalTotal.textContent = "error";
    nodes.evalIntent.textContent = "-";
    nodes.evalSafety.textContent = "-";
    nodes.evalRag.textContent = "-";
    return;
  }
  nodes.evalTotal.textContent = `${report.total} cases`;
  nodes.evalIntent.textContent = formatPercent(report.intent_accuracy);
  nodes.evalSafety.textContent = formatPercent(report.safety_block_recall);
  nodes.evalRag.textContent = formatPercent(report.rag_hit_rate);
}

export function formatPercent(value) {
  return `${Math.round(Number(value) * 100)}%`;
}
