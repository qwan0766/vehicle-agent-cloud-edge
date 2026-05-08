export function renderFeedback(nodes, feedback) {
  nodes.feedbackStatus.textContent = feedback.event_status || "未记录";
  nodes.feedbackEvent.textContent = feedback.event_log || "-";
  nodes.feedbackPreference.textContent = feedback.preference_update || "-";
}
