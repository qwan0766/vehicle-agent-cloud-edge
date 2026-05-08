import { renderMarkdown, escapeHtml } from "../markdown.js";
import { renderRuntimeTrace, renderGraphPath, agentClass } from "./trace.js";

export function renderResult(nodes, payload, helpers) {
  const { request, result, agent_trace: agentTrace } = payload;
  const pendingAction = result.pending_action || {};
  nodes.requestIdValue.textContent = request.request_id;
  nodes.commandTypeValue.textContent = request.command_type;
  nodes.safetyValue.textContent = request.safety;
  nodes.executionValue.textContent = result.status;
  const needsClarification = result.status === "NEEDS_CLARIFICATION";
  const needsDriverConfirmation = result.status === "NEEDS_DRIVER_CONFIRMATION";
  const needsChargeConfirmation = result.status === "NEEDS_CHARGE_CONFIRMATION";
  if (needsClarification) {
    renderClarification(
      nodes,
      result.clarification || {},
      result.output,
      pendingAction,
      helpers.confirmPendingAction,
      helpers.runCommand
    );
  } else if (needsDriverConfirmation || needsChargeConfirmation) {
    renderPendingConfirmation(nodes, result.output, pendingAction, helpers.confirmPendingAction);
  } else {
    renderMarkdown(nodes.resultOutput, result.output);
  }
  nodes.traceMode.textContent =
    needsClarification
      ? "需要确认"
      : needsDriverConfirmation
      ? "驾驶员确认"
      : needsChargeConfirmation
      ? "补能确认"
      : result.status === "BLOCKED"
      ? "安全拦截"
      : request.network === "ONLINE"
      ? "端云协同"
      : "本地兜底";

  if (needsClarification) {
    nodes.safetyBadge.textContent = "需要确认";
  } else if (needsDriverConfirmation) {
    nodes.safetyBadge.textContent = "待驾驶员确认";
  } else if (needsChargeConfirmation) {
    nodes.safetyBadge.textContent = "需要补能确认";
  } else if (result.status === "BLOCKED") {
    nodes.safetyBadge.textContent =
      request.safety === "DANGEROUS" ? "危险拦截" : "策略拦截";
  } else {
    nodes.safetyBadge.textContent = "安全正常";
  }
  nodes.safetyBadge.classList.toggle("badge-danger", result.status === "BLOCKED");
  nodes.safetyBadge.classList.toggle(
    "badge-clarification",
    needsClarification || needsDriverConfirmation || needsChargeConfirmation
  );
  nodes.safetyBadge.classList.toggle(
    "badge-safe",
    result.status !== "BLOCKED" &&
      !needsClarification &&
      !needsDriverConfirmation &&
      !needsChargeConfirmation
  );

  nodes.agentTrace.innerHTML = "";
  agentTrace.forEach((agent) => {
    const item = document.createElement("li");
    item.textContent = agent;
    item.className = agentClass(agent);
    nodes.agentTrace.appendChild(item);
  });

  renderRuntimeTrace(nodes, payload.runtime_trace || [], result.status);
  renderGraphPath(nodes, payload.graph || {});
  helpers.renderRouteSummary(nodes, payload.route_summary || {}, payload.charge_stations || []);
  helpers.renderRagContext(nodes, payload.rag_context || []);
  helpers.renderFeedback(nodes, payload.feedback || {});
  helpers.renderLocalContext(nodes, payload.local_context || {});
}

export function renderClarification(
  nodes,
  clarification,
  fallbackOutput,
  pendingAction,
  confirmPendingAction,
  runCommand
) {
  const payload = clarification || {};
  const suggestions = Array.isArray(payload.suggestions) ? payload.suggestions : [];
  const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
  nodes.resultOutput.innerHTML = "";

  const card = document.createElement("article");
  card.className = "clarification-card";

  const title = document.createElement("strong");
  title.textContent = "需要确认目的地";
  const question = document.createElement("p");
  question.textContent = payload.question || fallbackOutput || "请补充更具体的目的地。";
  const meta = document.createElement("small");
  meta.textContent = payload.query
    ? `待确认：${payload.query} · ${payload.reason || "unclear_destination"}`
    : payload.reason || "unclear_destination";

  card.append(title, question, meta);

  if (suggestions.length) {
    const suggestionBox = document.createElement("div");
    suggestionBox.className = "clarification-suggestions";
    suggestions.forEach((suggestion) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = suggestion;
      button.addEventListener("click", () => {
        nodes.commandInput.value = suggestion;
        nodes.commandInput.focus();
      });
      suggestionBox.appendChild(button);
    });
    card.appendChild(suggestionBox);
  }

  if (candidates.length) {
    const candidateBox = document.createElement("div");
    candidateBox.className = "clarification-candidates";
    candidates.forEach((candidate) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "clarification-candidate";
      const confidence =
        typeof candidate.confidence === "number"
          ? `${Math.round(candidate.confidence * 100)}%`
          : "未知";
      button.innerHTML =
        `<strong>${escapeHtml(candidate.name || "候选地点")}</strong>` +
        `<span>${escapeHtml(candidate.address || candidate.gps || "无地址")}</span>` +
        `<small>置信度 ${escapeHtml(confidence)} · ${escapeHtml(candidate.source || "provider")}</small>`;
      button.addEventListener("click", () => {
        if (pendingAction && pendingAction.id) {
          confirmPendingAction(pendingAction, {
            confirmed: true,
            selection: candidate,
          });
          return;
        }
        const confirmedTarget = candidate.gps || candidate.name || payload.query || "";
        nodes.commandInput.value = confirmedTarget ? `导航去${confirmedTarget}` : "";
        if (confirmedTarget && runCommand) {
          runCommand();
        } else {
          nodes.commandInput.focus();
        }
      });
      candidateBox.appendChild(button);
    });
    card.appendChild(candidateBox);
  }

  nodes.resultOutput.appendChild(card);
}

export function renderPendingConfirmation(nodes, output, pendingAction, confirmPendingAction) {
  nodes.resultOutput.innerHTML = "";
  const card = document.createElement("article");
  card.className = "clarification-card";

  const title = document.createElement("strong");
  title.textContent =
    pendingAction.type === "charge_confirmation" ? "需要确认补能策略" : "需要驾驶员确认";
  const message = document.createElement("p");
  message.textContent = output || "该操作需要确认后才能继续。";
  const meta = document.createElement("small");
  meta.textContent = pendingAction.id
    ? `pendingAction.id: ${pendingAction.id}`
    : "当前没有可恢复的待确认任务";

  const actions = document.createElement("div");
  actions.className = "confirmation-actions";
  const confirmButton = document.createElement("button");
  confirmButton.type = "button";
  confirmButton.textContent = "确认继续";
  confirmButton.disabled = !pendingAction.id;
  confirmButton.addEventListener("click", () => {
    confirmPendingAction(pendingAction, { confirmed: true });
  });

  const cancelButton = document.createElement("button");
  cancelButton.type = "button";
  cancelButton.textContent = "取消";
  cancelButton.disabled = !pendingAction.id;
  cancelButton.addEventListener("click", () => {
    confirmPendingAction(pendingAction, { confirmed: false });
  });

  actions.append(confirmButton, cancelButton);
  card.append(title, message, meta, actions);
  nodes.resultOutput.appendChild(card);
}

export function renderCommandError(nodes, error, helpers) {
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
  renderGraphPath(nodes, {});
  helpers.renderLocalContext(nodes, {});
  helpers.renderRouteSummary(nodes, {}, []);
  helpers.renderFeedback(nodes, {});
}

export function clearCommandError(nodes) {
  nodes.commandError.hidden = true;
  nodes.commandError.textContent = "";
}

export function errorInfoToHtml(title, message, info) {
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
