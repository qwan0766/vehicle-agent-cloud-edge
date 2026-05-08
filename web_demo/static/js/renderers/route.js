export function renderRouteSummary(nodes, route, stations) {
  nodes.routeProvider.textContent = route.destination_name
    ? `${route.provider} -> ${route.destination_name}`
    : route.provider || "无路线";
  nodes.routeDistance.textContent = route.distance_km !== undefined ? `${route.distance_km} km` : "-";
  nodes.routeDuration.textContent = route.duration_minutes !== undefined ? `${route.duration_minutes} 分钟` : "-";
  nodes.routeStrategy.textContent = route.strategy || "-";
  nodes.chargeStations.innerHTML = "";
  if (!stations.length) {
    nodes.chargeStations.textContent = "当前链路未查询充电站";
    return;
  }
  stations.forEach((station) => {
    const row = document.createElement("article");
    row.className = "station-row";
    const name = document.createElement("strong");
    name.textContent = station.name;
    const meta = document.createElement("span");
    meta.textContent = `${station.distance_km} km | ${station.status}`;
    row.append(name, meta);
    nodes.chargeStations.appendChild(row);
  });
}
