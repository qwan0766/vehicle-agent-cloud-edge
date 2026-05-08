import {
  getInitialState,
  confirmActionRequest,
  runCommandRequest,
  updateVehicleStateRequest,
  getVehicleEvents,
  runProviderSmokeTestRequest,
  getAcceptance,
} from "./js/api.js";
import { nodes } from "./js/dom.js";
import { state } from "./js/state.js";
import {
  applyVehicleState,
  bindEvents,
  runCommand,
  setNetwork,
  startVehicleEventPolling,
} from "./js/events.js";
import {
  renderVehicle,
  renderAutoEvents,
  renderOfflineEvaluation,
} from "./js/renderers/vehicle.js";
import {
  renderUsers,
  renderScenarioButtons,
  renderDemoSteps,
} from "./js/renderers/demo.js";
import {
  clearCommandError,
  renderCommandError,
  renderResult,
} from "./js/renderers/result.js";
import { renderAcceptance } from "./js/renderers/acceptance.js";
import { renderProviders, renderSmokeResults } from "./js/renderers/providers.js";
import { renderRouteSummary } from "./js/renderers/route.js";
import { renderRagContext } from "./js/renderers/rag.js";
import { renderFeedback } from "./js/renderers/feedback.js";
import { renderLocalContext } from "./js/renderers/local-context.js";

const api = {
  getInitialState,
  confirmActionRequest,
  runCommandRequest,
  updateVehicleStateRequest,
  getVehicleEvents,
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
    const runCommandForRenderers = () => runCommand(deps);
    const applyVehicleStateForRenderers = (updates) => applyVehicleState(deps, updates);

    renderVehicle(nodes, payload.vehicle_state, {}, state);
    renderAutoEvents(nodes, payload.auto_events || [], payload.auto_event_rules || []);
    renderOfflineEvaluation(nodes, payload.offline_evaluation);
    renderAcceptance(nodes, payload.acceptance);
    renderProviders(nodes, payload.providers);
    renderUsers(nodes, state);
    renderScenarioButtons(nodes, state, setNetworkForRenderers, runCommandForRenderers);
    renderDemoSteps(
      nodes,
      state,
      setNetworkForRenderers,
      applyVehicleStateForRenderers,
      runCommandForRenderers
    );
    bindEvents(deps);
    startVehicleEventPolling(deps);
  } catch (error) {
    renderCommandError(nodes, error, {
      renderRouteSummary,
      renderFeedback,
      renderLocalContext,
    });
  }
}

init();
