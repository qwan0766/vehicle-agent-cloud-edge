import { escapeHtml } from "../markdown.js";

export function renderRagContext(nodes, items) {
  nodes.ragCount.textContent = `${items.length} 条`;
  nodes.ragContext.innerHTML = "";

  if (!items.length) {
    nodes.ragContext.textContent = "没有召回相关知识";
    return;
  }

  items.forEach((item) => {
    const doc = document.createElement("article");
    doc.className = "rag-doc";

    const header = document.createElement("header");
    const stage = document.createElement("span");
    stage.textContent = item.stage;
    const score = document.createElement("span");
    score.textContent = `score ${item.score}`;
    header.append(stage, score);

    const text = document.createElement("strong");
    text.textContent = item.text;

    const keywords = document.createElement("small");
    keywords.textContent = item.matched_keywords.length
      ? `命中关键词：${item.matched_keywords.join("、")}`
      : `文档ID：${item.doc_id}`;

    doc.append(header, text, keywords);
    nodes.ragContext.appendChild(doc);
  });
}
