export async function getInitialState() {
  const response = await fetch("/api/state");
  return parseJsonResponse(response);
}

export async function runCommandRequest(payload) {
  const response = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response);
}

export async function confirmActionRequest(payload) {
  const response = await fetch("/api/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response);
}

export async function updateVehicleStateRequest(payload) {
  const response = await fetch("/api/vehicle-state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response);
}

export async function getVehicleEvents() {
  const response = await fetch("/api/vehicle-events");
  return parseJsonResponse(response);
}

export async function getOfflineEvaluation() {
  const response = await fetch("/api/offline-evaluation");
  return parseJsonResponse(response);
}

export async function runProviderSmokeTestRequest() {
  const response = await fetch("/api/provider-smoke", { method: "POST" });
  return parseJsonResponse(response);
}

export async function getAcceptance() {
  const response = await fetch("/api/acceptance");
  return parseJsonResponse(response);
}

export async function parseJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    const errorInfo = payload.error || {};
    const message = errorInfo.user_message || errorInfo.message || `HTTP ${response.status}`;
    const error = new Error(message);
    error.info = errorInfo;
    throw error;
  }
  return payload;
}
