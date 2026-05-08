export function renderAcceptance(nodes, report) {
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
