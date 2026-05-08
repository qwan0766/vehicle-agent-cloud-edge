export function renderProviders(nodes, providers) {
  nodes.providerLlm.textContent = providers.llm;
  nodes.providerLocalLlm.textContent = providers.local_llm || "-";
  nodes.providerOrchestrator.textContent = providers.orchestrator || "-";
  nodes.providerMap.textContent = providers.map;
  nodes.providerWeather.textContent = providers.weather;
  nodes.providerCharge.textContent = providers.charge;
}

export function renderSmokeResults(nodes, results) {
  nodes.smokeResults.innerHTML = "";
  results.forEach((item) => {
    const row = document.createElement("article");
    row.className = `smoke-row ${item.status.toLowerCase()}`;
    const name = document.createElement("strong");
    name.textContent = item.name;
    const status = document.createElement("span");
    status.textContent = item.status;
    row.append(name, status);
    nodes.smokeResults.appendChild(row);
  });
}
