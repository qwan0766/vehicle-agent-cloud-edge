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

export function renderAlignedTrace(nodes, agents, items, context = {}) {
  nodes.agentTrace.innerHTML = "";
  nodes.runtimeTrace.hidden = true;
  nodes.runtimeTrace.innerHTML = "";

  const agentList = Array.isArray(agents) ? agents : [];
  const toolItems = Array.isArray(items) ? items : [];

  if (!agentList.length) {
    const item = document.createElement("li");
    item.className = "trace-pair";
    item.append(
      renderAgentCard("Agent 链路未生成"),
      renderOutputCard([{ tool_name: "trace.empty", duration_ms: "-", output: "当前没有可展示的 Agent 调用链。" }])
    );
    nodes.agentTrace.appendChild(item);
    return;
  }

  agentList.forEach((agent) => {
    const pair = document.createElement("li");
    pair.className = `trace-pair ${agentClass(agent)}`.trim();
    const matchedTools = toolItems.filter((tool) => toolBelongsToAgent(tool.tool_name || "", agent));
    pair.append(
      renderAgentCard(agent),
      renderOutputCard(matchedTools.length ? matchedTools : defaultAgentOutputs(agent, context))
    );
    nodes.agentTrace.appendChild(pair);
  });
}

function renderAgentCard(agent) {
  const card = document.createElement("section");
  card.className = "agent-card";

  const name = document.createElement("strong");
  name.textContent = agent;
  const description = document.createElement("span");
  description.className = "agent-description";
  description.textContent = agentDescription(agent);
  card.append(name, description);
  return card;
}

function renderOutputCard(items) {
  const card = document.createElement("section");
  card.className = "agent-output-card";

  items.forEach((item) => {
    if (item.empty) {
      const empty = document.createElement("span");
      empty.className = "agent-output-empty";
      empty.textContent = item.output;
      card.appendChild(empty);
      return;
    }
    card.appendChild(renderToolCall(item));
  });

  return card;
}

function renderToolCall(item) {
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
  return row;
}

function defaultAgentOutputs(agent, context) {
  const request = context.request || {};
  const result = context.result || {};
  if (agent.includes("LocalIntentAgent")) {
    return [
      {
        tool_name: "local.intent",
        duration_ms: "-",
        output: `意图：${request.command_type || "-"}；输入：${request.content || "-"}`,
      },
    ];
  }
  if (agent.includes("GlobalSafetyDispatchAgent")) {
    return [
      {
        tool_name: "safety.dispatch",
        duration_ms: "-",
        output: `安全等级：${request.safety || "-"}；执行状态：${result.status || "-"}`,
      },
    ];
  }
  if (agent.includes("GlobalDispatchAgent")) {
    return [
      {
        tool_name: "dispatch.route",
        duration_ms: "-",
        output: `网络：${request.network || "-"}；选择端云协同或本地执行路径。`,
      },
    ];
  }
  if (agent.includes("DataUploadAgent")) {
    return [
      {
        tool_name: "data.loop",
        duration_ms: "-",
        output: "记录本次指令、执行状态和可学习的偏好变化。",
      },
    ];
  }
  if (agent.includes("ProviderError")) {
    return [
      {
        tool_name: "provider.error",
        duration_ms: "-",
        output: result.output || "外部接口调用失败。",
      },
    ];
  }
  if (agent.includes("Block")) {
    return [
      {
        tool_name: "safety.block",
        duration_ms: "-",
        output: "安全阀门已拦截，未继续调用云端工具。",
      },
    ];
  }
  return [{ empty: true, output: "本 Agent 本次未产生独立工具输出。" }];
}

function toolBelongsToAgent(toolName, agent) {
  if (!toolName) {
    return false;
  }
  if (agent.includes("UserProfileAgent")) {
    return toolName.startsWith("user_profile.");
  }
  if (agent.includes("VectorKnowledgeAgent")) {
    return toolName.startsWith("knowledge.");
  }
  if (agent.includes("ExternalEcologyAgent")) {
    return toolName.startsWith("ecology.");
  }
  if (agent.includes("GlobalTripPlanningAgent") || agent.includes("TripPlanning")) {
    return (
      toolName.startsWith("trip.") ||
      toolName.startsWith("provider.geocode") ||
      toolName.startsWith("provider.map")
    );
  }
  if (agent.includes("GlobalDispatchAgent")) {
    return toolName.startsWith("decision.");
  }
  if (agent.includes("DataUploadAgent")) {
    return toolName.startsWith("data.");
  }
  if (agent.includes("ProviderError")) {
    return toolName.startsWith("provider.error");
  }
  return false;
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

export function agentDescription(agent) {
  if (agent.includes("LocalIntentAgent")) {
    return "解析用户指令意图，结合本地上下文做输入理解。";
  }
  if (agent.includes("GlobalSafetyDispatchAgent")) {
    return "进行车规安全策略判断，决定放行、确认或拦截。";
  }
  if (agent.includes("GlobalDispatchAgent")) {
    return "端云全局调度入口，选择云端图或本地执行路径。";
  }
  if (agent.includes("UserProfileAgent")) {
    return "读取用户画像和长期偏好，用于个性化决策。";
  }
  if (agent.includes("VectorKnowledgeAgent")) {
    return "召回本地和云端知识，为规划提供 RAG 依据。";
  }
  if (agent.includes("ExternalEcologyAgent")) {
    return "聚合天气、补能站和地图生态数据。";
  }
  if (agent.includes("GlobalTripPlanningAgent") || agent.includes("TripPlanning")) {
    return "结合路线、补能和偏好生成出行方案。";
  }
  if (agent.includes("DataUploadAgent")) {
    return "记录执行事件和偏好变化，形成数据闭环。";
  }
  if (agent.includes("CabinVehicleControl")) {
    return "执行座舱舒适性控制，不触碰动力和制动。";
  }
  if (agent.includes("EnergyPolicy")) {
    return "根据电量和行程判断是否需要补能建议。";
  }
  if (agent.includes("ProviderError")) {
    return "外部接口调用失败，保留错误原因供排查。";
  }
  if (agent.includes("Block")) {
    return "安全阀门已阻断后续工具调用。";
  }
  return "参与当前任务链路的子 Agent。";
}
