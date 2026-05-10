import {
  getInitialState,
  confirmActionRequest,
  runCommandRequest,
  updateVehicleStateRequest,
  getVehicleEvents,
  getOfflineEvaluation,
  runProviderSmokeTestRequest,
  getAcceptance,
} from "./js/api.js?v=agent-trace-aligned-20260510";
import { nodes } from "./js/dom.js?v=agent-trace-aligned-20260510";
import { state } from "./js/state.js?v=agent-trace-aligned-20260510";
import {
  applyVehicleState,
  bindEvents,
  runCommand,
  setNetwork,
  startVehicleEventPolling,
} from "./js/events.js?v=agent-trace-aligned-20260510";
import {
  renderVehicle,
  renderAutoEvents,
  renderOfflineEvaluation,
} from "./js/renderers/vehicle.js?v=agent-trace-aligned-20260510";
import {
  renderUsers,
  renderScenarioButtons,
  renderDemoSteps,
} from "./js/renderers/demo.js?v=agent-trace-aligned-20260510";
import {
  clearCommandError,
  renderCommandError,
  renderResult,
} from "./js/renderers/result.js?v=agent-trace-aligned-20260510";
import { renderAcceptance } from "./js/renderers/acceptance.js?v=agent-trace-aligned-20260510";
import { renderProviders, renderSmokeResults } from "./js/renderers/providers.js?v=agent-trace-aligned-20260510";
import { renderRouteSummary } from "./js/renderers/route.js?v=agent-trace-aligned-20260510";
import { renderRagContext } from "./js/renderers/rag.js?v=agent-trace-aligned-20260510";
import { renderFeedback } from "./js/renderers/feedback.js?v=agent-trace-aligned-20260510";
import { renderLocalContext } from "./js/renderers/local-context.js?v=agent-trace-aligned-20260510";

const api = {
  getInitialState,
  confirmActionRequest,
  runCommandRequest,
  updateVehicleStateRequest,
  getVehicleEvents,
  getOfflineEvaluation,
  runProviderSmokeTestRequest,
  getAcceptance,
};

const renderers = {
  renderVehicle,
  renderAutoEvents,
  renderOfflineEvaluation,
  renderUsers,
  renderScenarioButtons,
  renderDemoSteps,
  clearCommandError,
  renderCommandError,
  renderResult,
  renderAcceptance,
  renderProviders,
  renderSmokeResults,
  renderRouteSummary,
  renderRagContext,
  renderFeedback,
  renderLocalContext,
};

const deps = {
  nodes,
  state,
  api,
  renderers,
};

async function init() {
  try {
    const payload = await getInitialState();
    state.scenarios = payload.scenarios;
    state.demoSteps = payload.demo_steps || [];
    state.users = payload.users;

    const setNetworkForRenderers = (network) => setNetwork(nodes, state, network);
    const applyVehicleStateForRenderers = (updates) => applyVehicleState(deps, updates);

    renderVehicle(nodes, payload.vehicle_state, {}, state);
    renderAutoEvents(nodes, payload.auto_events || [], payload.auto_event_rules || []);
    renderOfflineEvaluation(nodes, payload.offline_evaluation);
    renderAcceptance(nodes, payload.acceptance);
    renderProviders(nodes, payload.providers);
    renderUsers(nodes, state);
    renderScenarioButtons(nodes, state, setNetworkForRenderers);
    renderDemoSteps(
      nodes,
      state,
      setNetworkForRenderers,
      applyVehicleStateForRenderers,
      () => runCommand(deps)
    );
    bindEvents(deps);
    startVehicleEventPolling(deps);
    loadOfflineEvaluation(deps);
  } catch (error) {
    renderCommandError(nodes, error, {
      renderRouteSummary,
      renderFeedback,
      renderLocalContext,
    });
  }
}

async function loadOfflineEvaluation(deps) {
  const { nodes, api, renderers } = deps;
  try {
    const payload = await api.getOfflineEvaluation();
    renderers.renderOfflineEvaluation(nodes, payload);
  } catch (error) {
    renderers.renderOfflineEvaluation(nodes, {
      status: "ERROR",
      total: 0,
      intent_accuracy: 0,
      safety_block_recall: 0,
      rag_hit_rate: 0,
    });
  }
}

init();
