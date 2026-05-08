# Web Demo Layout Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the execution result into the primary workflow area and reduce dashboard clutter.

**Architecture:** Keep the existing static HTML/CSS/JS architecture. Change DOM order so layout does not depend on CSS `order`, and use lightweight section labels to separate primary workflow from engineering observability.

**Tech Stack:** Static HTML, CSS Grid, Python unittest/pytest, existing Web QA script.

---

### Task 1: Lock Layout Structure With Tests

**Files:**
- Modify: `tests/test_web_demo_markup.py`

- [ ] Add tests asserting `.result-panel` appears before `.demo-panel`, `.trace-panel`, and `.rag-panel`.
- [ ] Run the targeted markup test and verify it fails before implementation.

### Task 2: Reorder Dashboard DOM

**Files:**
- Modify: `web_demo/static/index.html`

- [ ] Move `<section class="panel result-panel">` directly after `<section class="panel command-panel">`.
- [ ] Add lightweight visual separators for the primary workflow and engineering observability areas.

### Task 3: Simplify Layout CSS

**Files:**
- Modify: `web_demo/static/styles.css`

- [ ] Remove CSS `order` rules that attempted to reorder grid items.
- [ ] Add styling for the new section separators.
- [ ] Keep responsive behavior intact on mobile.

### Task 4: Verify And Commit

**Files:**
- Update: `reports/web_qa_report.md`
- Update: `reports/web_qa_report.json`
- Update: `reports/browser_qa/desktop.png`

- [ ] Run targeted markup tests.
- [ ] Run Web QA with screenshots against `http://127.0.0.1:8031`.
- [ ] Run full test suite.
- [ ] Commit with message `refactor: streamline web demo layout`.
