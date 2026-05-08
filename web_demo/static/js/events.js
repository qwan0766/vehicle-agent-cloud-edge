export function bindEvents(deps) {
  const { nodes, state } = deps;

  nodes.onlineBtn.addEventListener("click", () => setNetwork(nodes, state, "ONLINE"));
  nodes.offlineBtn.addEventListener("click", () => setNetwork(nodes, state, "OFFLINE"));
  nodes.runBtn.addEventListener("click", () => runCommand(deps));
  nodes.updateVehicleStateBtn.addEventListener("click", () => updateVehicleState(deps));
  nodes.smokeBtn.addEventListener("click", () => runSmokeTest(deps));
  nodes.acceptanceRefreshBtn.addEventListener("click", () => refreshAcceptance(deps));
  nodes.userSelect.addEventListener("change", () => {
    state.userId = nodes.userSelect.value;
    nodes.userIdValue.textContent = state.userId;
  });
  nodes.commandInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      runCommand(deps);
    }
  });
}

export function setNetwork(nodes, state, network) {
  state.network = network;
  nodes.onlineBtn.classList.toggle("active", network === "ONLINE");
  nodes.offlineBtn.classList.toggle("active", network === "OFFLINE");
  nodes.networkBadge.textContent = network;
}

export async function updateVehicleState(deps) {
  const { nodes, state, api, renderers } = deps;
  nodes.updateVehicleStateBtn.disabled = true;
  nodes.updateVehicleStateBtn.textContent = "更新中";
  try {
    await applyVehicleState(deps, {
      road_type: nodes.roadTypeInput.value,
      speed_limit_kmh: nodes.speedLimitInput.value,
      speed_kmh: nodes.vehicleSpeedInput.value,
      battery_percent: nodes.batteryInput.value,
      driver_assist_mode: nodes.assistModeInput.value,
    });
  } catch (error) {
    renderers.renderCommandError(nodes, error, resultHelpers(deps));
  } finally {
    nodes.updateVehicleStateBtn.disabled = false;
    nodes.updateVehicleStateBtn.textContent = "应用状态";
  }
}

export async function applyVehicleState(deps, updates) {
  const { nodes, state, api, renderers } = deps;
  const payload = await api.updateVehicleStateRequest(updates || {});
  renderers.renderVehicle(nodes, payload.vehicle_state, {}, state);
  renderers.renderAutoEvents(nodes, payload.auto_events || [], payload.auto_event_rules || []);
  return payload;
}

export function startVehicleEventPolling(deps) {
  refreshVehicleEvents(deps);
  return setInterval(() => refreshVehicleEvents(deps), 3000);
}

export async function refreshVehicleEvents(deps) {
  const { nodes, state, api, renderers } = deps;
  try {
    const payload = await api.getVehicleEvents();
    renderers.renderVehicle(nodes, payload.vehicle_state, {
      syncControls: false,
      syncNetwork: false,
    }, state);
    renderers.renderAutoEvents(nodes, payload.events || [], payload.event_rules || []);
  } catch (error) {
    const item = document.createElement("article");
    item.className = "auto-event active critical";
    const title = document.createElement("strong");
    title.textContent = "状态事件刷新失败";
    const message = document.createElement("span");
    message.textContent = error.message;
    item.append(title, message);
    nodes.autoEvents.innerHTML = "";
    nodes.autoEvents.appendChild(item);
  }
}

export async function refreshAcceptance(deps) {
  const { nodes, api, renderers } = deps;
  nodes.acceptanceRefreshBtn.disabled = true;
  nodes.acceptanceRefreshBtn.textContent = "读取中";
  try {
    const payload = await api.getAcceptance();
    renderers.renderAcceptance(nodes, payload);
  } catch (error) {
    nodes.acceptanceStatus.textContent = "ERROR";
    nodes.acceptanceStatus.className = "status-danger";
    nodes.acceptanceSteps.textContent = `验收报告读取失败：${error.message}`;
  } finally {
    nodes.acceptanceRefreshBtn.disabled = false;
    nodes.acceptanceRefreshBtn.textContent = "刷新";
  }
}

export async function runSmokeTest(deps) {
  const { nodes, api, renderers } = deps;
  nodes.smokeBtn.disabled = true;
  nodes.smokeBtn.textContent = "检测中";
  nodes.smokeResults.textContent = "正在调用真实接口";
  try {
    const payload = await api.runProviderSmokeTestRequest();
    renderers.renderSmokeResults(nodes, payload.results || []);
  } catch (error) {
    nodes.smokeResults.textContent = `接口检测失败：${error.message}`;
  } finally {
    nodes.smokeBtn.disabled = false;
    nodes.smokeBtn.textContent = "Smoke Test";
  }
}

export async function runCommand(deps) {
  const { nodes, state, api, renderers } = deps;
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
  renderers.clearCommandError(nodes);
  try {
    const payload = await api.runCommandRequest({
      content,
      user_id: userId,
      network,
    });
    if (requestId !== state.activeRequestId) {
      return;
    }
    renderers.renderVehicle(nodes, payload.vehicle_state, {}, state);
    renderers.renderResult(nodes, payload, resultHelpers(deps));
  } catch (error) {
    if (requestId !== state.activeRequestId) {
      return;
    }
    renderers.renderCommandError(nodes, error, resultHelpers(deps));
  } finally {
    if (requestId === state.activeRequestId) {
      nodes.runBtn.disabled = false;
      nodes.runBtn.textContent = "运行指令";
    }
  }
}

export async function confirmPendingAction(deps, pendingAction, options = {}) {
  const { nodes, state, api, renderers } = deps;
  if (!pendingAction || !pendingAction.id) {
    return;
  }

  const requestId = state.requestSeq + 1;
  state.requestSeq = requestId;
  state.activeRequestId = requestId;
  nodes.runBtn.disabled = true;
  nodes.runBtn.textContent = "确认中";
  nodes.resultOutput.textContent = "正在继续待确认任务";
  renderers.clearCommandError(nodes);

  try {
    const payload = await api.confirmActionRequest({
      action_id: pendingAction.id,
      user_id: state.userId,
      confirmed: options.confirmed !== false,
      selection: options.selection || {},
    });
    if (requestId !== state.activeRequestId) {
      return;
    }
    renderers.renderVehicle(nodes, payload.vehicle_state, {}, state);
    renderers.renderResult(nodes, payload, resultHelpers(deps));
  } catch (error) {
    if (requestId !== state.activeRequestId) {
      return;
    }
    renderers.renderCommandError(nodes, error, resultHelpers(deps));
  } finally {
    if (requestId === state.activeRequestId) {
      nodes.runBtn.disabled = false;
      nodes.runBtn.textContent = "运行指令";
    }
  }
}

function resultHelpers(deps) {
  const { renderers } = deps;
  return {
    renderRouteSummary: renderers.renderRouteSummary,
    renderRagContext: renderers.renderRagContext,
    renderFeedback: renderers.renderFeedback,
    renderLocalContext: renderers.renderLocalContext,
    runCommand: () => runCommand(deps),
    confirmPendingAction: (pendingAction, options) =>
      confirmPendingAction(deps, pendingAction, options),
  };
}
