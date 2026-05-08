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
