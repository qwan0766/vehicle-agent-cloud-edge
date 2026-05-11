import { escapeHtml } from "../markdown.js?v=knowledge-layer-v1-20260511";

export function renderUsers(nodes, state) {
  nodes.userSelect.innerHTML = "";
  state.users.forEach((user) => {
    const option = document.createElement("option");
    option.value = user.user_id;
    option.textContent = user.label;
    nodes.userSelect.appendChild(option);
  });
  nodes.userSelect.value = state.userId;
  nodes.userIdValue.textContent = state.userId;
}
export function renderScenarioButtons(nodes, state, setNetwork) {
  if (!nodes.scenarioButtons) {
    return;
  }
  nodes.scenarioButtons.innerHTML = "";
  state.scenarios.forEach((scenario) => {
    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML =
      `<strong>${escapeHtml(scenario.label)}</strong>` +
      `<span>${scenario.trigger === "AUTO" ? "自动触发" : "手动演示"}</span>`;
    button.addEventListener("click", () => {
      nodes.commandInput.value = scenario.content;
      setNetwork(scenario.network);
      nodes.commandInput.focus();
    });
    nodes.scenarioButtons.appendChild(button);
  });
}

export function renderDemoSteps(nodes, state, setNetwork, applyVehicleState, runCommand) {
  nodes.demoSteps.innerHTML = "";
  nodes.demoStepCount.textContent = `${state.demoSteps.length} steps`;
  if (!state.demoSteps.length) {
    nodes.demoSteps.textContent = "暂无演示按钮";
    return;
  }

  state.demoSteps.forEach((step) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "demo-step";
    button.dataset.demoId = step.id;

    const title = document.createElement("strong");
    title.textContent = step.title;
    const meta = document.createElement("span");
    const displayMode = step.display_mode || step.network;
    meta.textContent = `${displayMode} · ${step.content}`;
    button.append(title, meta);
    button.addEventListener("click", async () =>
      activateDemoStep(nodes, state, step, false, setNetwork, applyVehicleState, runCommand)
    );
    nodes.demoSteps.appendChild(button);
  });

  activateDemoStep(nodes, state, state.demoSteps[0], false, setNetwork, applyVehicleState, runCommand);
}

export async function activateDemoStep(
  nodes,
  state,
  step,
  shouldRun,
  setNetwork,
  applyVehicleState,
  runCommand
) {
  state.activeDemoId = step.id;
  nodes.commandInput.value = step.content;
  setNetwork(step.network);
  renderDemoNotes(nodes, step);
  nodes.commandInput.focus();
  document.querySelectorAll(".demo-step").forEach((button) => {
    button.classList.toggle("active", button.dataset.demoId === step.id);
  });
  if (step.vehicle_state) {
    await applyVehicleState(step.vehicle_state);
  }
  if (shouldRun) {
    runCommand();
  }
}

export function renderDemoNotes(nodes, step) {
  nodes.demoFocus.textContent = step.focus;
  nodes.demoTalkTrack.textContent = step.talk_track;
  nodes.demoExpectedPanels.innerHTML = "";
  (step.expected_panels || []).forEach((panel) => {
    const tag = document.createElement("span");
    tag.textContent = panel;
    nodes.demoExpectedPanels.appendChild(tag);
  });
}
