export function renderLocalContext(nodes, context) {
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
  renderSummarySegments(nodes.localContextSummary, payload.summary || "");
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

export function renderSummarySegments(container, summary) {
  container.innerHTML = "";
  const segments = formatSummarySegments(summary);

  if (!segments.length) {
    container.textContent = "暂无压缩摘要";
    return;
  }

  const list = document.createElement("ol");
  list.className = "local-context-summary-list";

  segments.forEach((segment) => {
    const item = document.createElement("li");
    item.className = "summary-segment";

    const meta = document.createElement("span");
    meta.className = "summary-status";
    meta.textContent = segment.status
      ? `${segment.kind} · ${segment.status}`
      : segment.kind;

    const title = document.createElement("strong");
    title.className = "summary-user";
    title.textContent = segment.user || segment.title;

    const body = document.createElement("small");
    body.textContent = segment.body;

    item.append(meta, title, body);
    list.appendChild(item);
  });

  container.appendChild(list);
}

export function formatSummarySegments(summary) {
  const text = String(summary || "").trim();
  if (!text) {
    return [];
  }

  return text
    .split(/\s+\|\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(-8)
    .map(parseSummarySegment);
}

function parseSummarySegment(segment) {
  const turnMatch = segment.match(
    /^([A-Z_]+):([A-Z_]+)\s+user=(.*?)\s*->\s*(.*)$/
  );
  if (turnMatch) {
    return {
      kind: turnMatch[1],
      status: turnMatch[2],
      user: compactText(turnMatch[3], 80),
      title: "本地记忆",
      body: compactText(turnMatch[4], 180),
    };
  }

  if (/^\{/.test(segment) || /^\[/.test(segment)) {
    return {
      kind: "STRUCTURED",
      status: "",
      user: "",
      title: "结构化摘要片段",
      body: compactText(segment, 180),
    };
  }

  return {
    kind: "SUMMARY",
    status: "",
    user: "",
    title: "摘要片段",
    body: compactText(segment, 180),
  };
}

function compactText(value, maxLength) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, Math.max(0, maxLength - 1))}…`;
}
