export function renderRuntimeTrace(nodes, items, status = "") {
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

export function renderGraphPath(nodes, graph) {
  const payload = graph || {};
  const path = Array.isArray(payload.path) ? payload.path : [];
  const mode = payload.mode || "not_run";
  const fallbackText = payload.fallback ? " · fallback" : "";
  nodes.graphMode.textContent = `${mode}${fallbackText}`;
  nodes.graphPath.textContent = path.length ? path.join(" -> ") : "未执行云端图";
}

export function agentClass(agent) {
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
    agent.includes("DataUpload") ||
    agent.includes("Clarification") ||
    agent.includes("EnergyPolicy")
  ) {
    return "local";
  }
  if (agent.includes("Block")) {
    return "blocked";
  }
  return "";
}
