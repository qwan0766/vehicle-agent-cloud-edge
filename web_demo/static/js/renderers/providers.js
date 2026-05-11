export function renderProviders(nodes, providers) {
  nodes.providerLlm.textContent = providers.llm;
  nodes.providerLocalLlm.textContent = providers.local_llm || "-";
  nodes.providerOrchestrator.textContent = providers.orchestrator || "-";
  nodes.providerMap.textContent = providers.map;
  nodes.providerWeather.textContent = providers.weather;
  nodes.providerCharge.textContent = providers.charge;
  nodes.providerCards.forEach((card) => {
    const health = card.querySelector("[data-provider-health]");
    if (!health || health.classList.contains("skip")) {
      return;
    }
    health.className = "provider-health pending";
    health.textContent = "待检测";
  });
}

export function renderSmokeResults(nodes, results) {
  const seen = new Set();
  results.forEach((item) => {
    const card = nodes.providerCards.find(
      (providerCard) => providerCard.dataset.smokeName === item.name
    );
    if (!card) {
      return;
    }
    seen.add(item.name);
    const health = card.querySelector("[data-provider-health]");
    health.className = `provider-health ${item.status.toLowerCase()}`;
    health.textContent = item.status;
  });
  nodes.smokeResults.textContent = seen.size
    ? `已更新 ${seen.size} 个外部 Provider 状态`
    : "没有匹配到可展示的 Provider 检测结果";
}
