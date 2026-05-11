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
  const parallelAgents = parallelAgentSet(context.graph || {});

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
    const isParallel = parallelAgents.has(agent);
    pair.className = `trace-pair ${agentClass(agent)} ${isParallel ? "parallel-group" : ""}`.trim();
    const matchedTools = toolItems.filter((tool) => toolMatchesAgent(tool, agent));
    pair.append(
      renderAgentCard(agent, { isParallel }),
      renderOutputCard(matchedTools.length ? matchedTools : defaultAgentOutputs(agent, context))
    );
    nodes.agentTrace.appendChild(pair);
  });
}

function renderAgentCard(agent, metadata = {}) {
  const card = document.createElement("section");
  card.className = "agent-card";

  const header = document.createElement("div");
  header.className = "agent-card-header";
  const name = document.createElement("strong");
  name.textContent = agent;
  const scope = document.createElement("span");
  scope.className = `agent-scope ${agentScopeClass(agent)}`.trim();
  scope.textContent = agentScope(agent);
  const badges = document.createElement("span");
  badges.className = "agent-badges";
  badges.append(scope);
  if (metadata.isParallel) {
    const parallelBadge = document.createElement("span");
    parallelBadge.className = "agent-parallel-badge";
    parallelBadge.textContent = "并行收集";
    badges.append(parallelBadge);
  }
  header.append(name, badges);

  const description = document.createElement("span");
  description.className = "agent-description";
  description.textContent = agentDescription(agent);
  card.append(header, description);
  return card;
}

export function parallelAgentSet(graph) {
  const groups = Array.isArray(graph.parallel_groups) ? graph.parallel_groups : [];
  const agents = new Set();
  groups.forEach((group) => {
    const nodes = Array.isArray(group.nodes) ? group.nodes : [];
    nodes.forEach((node) => {
      graphNodeAgents(node).forEach((agent) => agents.add(agent));
    });
  });
  return agents;
}

function graphNodeAgents(node) {
  const mapping = {
    profile: ["UserProfileAgent"],
    route_preference: ["UserProfileAgent"],
    knowledge: ["RuleKnowledgeAgent", "DocumentRAGAgent"],
    ecology: ["ExternalEcologyAgent"],
    route_provider: ["RouteProviderAgent"],
  };
  return mapping[node] || [];
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
  if (item.tool_name === "ecology.snapshot" && typeof item.output === "object") {
    row.append(header, renderEcologySnapshot(item.output));
    return row;
  }
  output.textContent = typeof item.output === "string" ? item.output : JSON.stringify(item.output);

  row.append(header, output);
  return row;
}

function renderEcologySnapshot(snapshot) {
  const container = document.createElement("div");
  container.className = "ecology-snapshot";

  const weather = snapshot.weather || {};
  const station = (snapshot.charge_stations || [])[0] || {};
  container.append(
    ecologyMetric("天气", weather.summary || "-", [
      `${weather.temperature_c ?? "-"}℃`,
      `降水 ${weather.precipitation_mm ?? "-"}mm`,
      `风 ${weather.wind_level || "-"}`,
      `来源 ${weather.source || "-"}`,
    ]),
    ecologyMetric("补能站", station.name || "-", [
      `${station.distance_km ?? "-"} km`,
      station.status || "-",
      `预计 ${station.estimated_minutes ?? "-"} 分钟`,
      `来源 ${snapshot.charge_source || "-"}`,
    ])
  );
  return container;
}

function ecologyMetric(label, title, details) {
  const card = document.createElement("section");
  card.className = "ecology-metric";
  const caption = document.createElement("span");
  caption.textContent = label;
  const name = document.createElement("strong");
  name.textContent = title;
  const meta = document.createElement("small");
  meta.textContent = details.filter(Boolean).join(" · ");
  card.append(caption, name, meta);
  return card;
}

function defaultAgentOutputs(agent, context) {
  const request = context.request || {};
  const result = context.result || {};
  if (agent.includes("GlobalDispatchAgent")) {
    return [
      {
        tool_name: "dispatch.route",
        duration_ms: "-",
        output: `网络：${request.network || "-"}；发起云端并行上下文收集，等待画像、知识库、生态数据汇聚后再进入规划。`,
      },
    ];
  }
  if (agent.includes("CloudDecisionAgent")) {
    return [
      {
        tool_name: "decision.pending",
        duration_ms: "-",
        output: "等待路线规划和上下文汇聚后生成最终执行说明。",
      },
    ];
  }
  if (agent.includes("RouteProviderAgent")) {
    return [
      {
        tool_name: "provider.pending",
        duration_ms: "-",
        output: "等待地理编码与地图路线工具返回。",
      },
    ];
  }
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
  if (agent.includes("DestinationClarification")) {
    return [
      {
        tool_name: "clarification.result",
        duration_ms: "-",
        output:
          result.output ||
          "目的地信息不足，已进入用户澄清流程，未继续调用云端规划链路。",
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

function toolMatchesAgent(tool, agent) {
  const agentId = tool.agent_id || "";
  if (agentId && traceAgentMatches(agentId, agent)) {
    return true;
  }
  return toolBelongsToAgent(tool.tool_name || "", agent);
}

function traceAgentMatches(agentId, agent) {
  if (agent.includes(agentId) || agentId.includes(agent)) {
    return true;
  }
  if (
    agentId === "VectorKnowledgeAgent" &&
    (agent.includes("RuleKnowledgeAgent") || agent.includes("DocumentRAGAgent"))
  ) {
    return true;
  }
  if (
    agentId === "GlobalDispatchAgent" &&
    (agent.includes("CloudDecisionAgent") || agent.includes("GlobalDispatchAgent"))
  ) {
    return true;
  }
  return false;
}

function toolBelongsToAgent(toolName, agent) {
  if (!toolName) {
    return false;
  }
  if (agent.includes("UserProfileAgent")) {
    return toolName.startsWith("user_profile.");
  }
  if (agent.includes("RuleKnowledgeAgent") || agent.includes("DocumentRAGAgent")) {
    return toolName.startsWith("knowledge.");
  }
  if (agent.includes("ExternalEcologyAgent")) {
    return toolName.startsWith("ecology.");
  }
  if (agent.includes("RouteProviderAgent")) {
    return toolName.startsWith("provider.geocode") || toolName.startsWith("provider.map");
  }
  if (agent.includes("GlobalTripPlanningAgent") || agent.includes("TripPlanning")) {
    return toolName.startsWith("trip.");
  }
  if (agent.includes("CloudDecisionAgent")) {
    return toolName.startsWith("decision.");
  }
  if (agent.includes("GlobalDispatchAgent")) {
    return toolName.startsWith("dispatch.");
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
  nodes.graphPath.textContent = path.length ? formatGraphPath(path, payload) : "未执行云端图";
}

function formatGraphPath(path, graph) {
  const groups = Array.isArray(graph.parallel_groups) ? graph.parallel_groups : [];
  const contextGroup = groups.find((group) => group.id === "cloud_context");
  const providerGroup = groups.find((group) => group.id === "route_provider_parallel");
  return path
    .map((node) => {
      if (node === "context_parallel" && contextGroup) {
        return `并行[${(contextGroup.nodes || []).join(" | ")}]`;
      }
      if (node === "provider_parallel" && providerGroup) {
        return `并行[${(providerGroup.nodes || []).join(" | ")}]`;
      }
      return node;
    })
    .join(" -> ");
}

export function agentClass(agent) {
  if (
    agent.includes("Cloud") ||
    agent.includes("GlobalDispatch") ||
    agent.includes("TripPlanning") ||
    agent.includes("RouteProvider") ||
    agent.includes("UserProfile") ||
    agent.includes("RuleKnowledge") ||
    agent.includes("DocumentRAG") ||
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

export function agentScope(agent) {
  if (agent.includes("CloudDecisionAgent")) {
    return "云端 Agent";
  }
  if (agent.includes("RouteProviderAgent")) {
    return "云端工具";
  }
  if (agent.includes("LocalIntentAgent")) {
    return "车端本地";
  }
  if (agent.includes("GlobalSafetyDispatchAgent") || agent.includes("Block")) {
    return "车端安全";
  }
  if (agent.includes("EnergyPolicy")) {
    return "车端状态";
  }
  if (agent.includes("DestinationClarification")) {
    return "车端澄清";
  }
  if (agent.includes("CabinVehicleControl") || agent.includes("Fallback")) {
    return "车端执行";
  }
  if (agent.includes("DataUploadAgent")) {
    return "数据闭环";
  }
  if (agent.includes("ProviderError")) {
    return "外部接口";
  }
  if (agent.includes("GlobalDispatchAgent")) {
    return "云端调度";
  }
  if (
    agent.includes("Cloud") ||
    agent.includes("TripPlanning") ||
    agent.includes("RouteProvider") ||
    agent.includes("UserProfile") ||
    agent.includes("RuleKnowledge") ||
    agent.includes("DocumentRAG") ||
    agent.includes("ExternalEcology")
  ) {
    return "云端 Agent";
  }
  return "子 Agent";
}

function agentScopeClass(agent) {
  if (agent.includes("CloudDecisionAgent")) {
    return "scope-cloud";
  }
  const scope = agentScope(agent);
  if (scope.startsWith("云端")) {
    return "scope-cloud";
  }
  if (scope.startsWith("云端")) {
    return "scope-cloud";
  }
  if (scope.startsWith("车端")) {
    return "scope-edge";
  }
  if (scope === "数据闭环") {
    return "scope-data";
  }
  if (scope === "外部接口") {
    return "scope-provider";
  }
  return "scope-neutral";
}

export function agentDescription(agent) {
  if (agent.includes("CloudDecisionAgent")) {
    return "汇聚画像、知识、生态和路线规划，生成最终执行说明。";
  }
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
  if (agent.includes("RuleKnowledgeAgent")) {
    return "读取结构化规则库，用确定性策略提供安全、补能和路线规则。";
  }
  if (agent.includes("DocumentRAGAgent")) {
    return "仅面向车主手册、服务政策等长文本问题做文档 RAG。";
  }
  if (agent.includes("ExternalEcologyAgent")) {
    return "聚合天气、补能站和地图生态数据。";
  }
  if (agent.includes("RouteProviderAgent")) {
    return "并行调用地理编码和地图路线工具，产出距离与耗时。";
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
