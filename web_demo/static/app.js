import {
  getInitialState,
  confirmActionRequest,
  runCommandRequest,
  updateVehicleStateRequest,
  getVehicleEvents,
  getOfflineEvaluation,
  runProviderSmokeTestRequest,
  getAcceptance,
} from "./js/api.js?v=knowledge-layer-v1-20260511";
import { nodes } from "./js/dom.js?v=knowledge-layer-v1-20260511";
import { state } from "./js/state.js?v=knowledge-layer-v1-20260511";
import {
  applyVehicleState,
  bindEvents,
  runCommand,
  setNetwork,
  startVehicleEventPolling,
} from "./js/events.js?v=knowledge-layer-v1-20260511";
import {
  renderVehicle,
  renderAutoEvents,
  renderOfflineEvaluation,
} from "./js/renderers/vehicle.js?v=knowledge-layer-v1-20260511";
import {
  renderUsers,
  renderDemoSteps,
} from "./js/renderers/demo.js?v=knowledge-layer-v1-20260511";
import {
  clearCommandError,
  renderCommandError,
  renderResult,
} from "./js/renderers/result.js?v=knowledge-layer-v1-20260511";
import { renderAcceptance } from "./js/renderers/acceptance.js?v=knowledge-layer-v1-20260511";
import { renderProviders, renderSmokeResults } from "./js/renderers/providers.js?v=knowledge-layer-v1-20260511";
import { renderRouteSummary } from "./js/renderers/route.js?v=knowledge-layer-v1-20260511";
import { renderRagContext } from "./js/renderers/rag.js?v=knowledge-layer-v1-20260511";
import { renderFeedback } from "./js/renderers/feedback.js?v=knowledge-layer-v1-20260511";
import { renderLocalContext } from "./js/renderers/local-context.js?v=knowledge-layer-v1-20260511";

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
