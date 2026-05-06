# Web QA Report

- Generated at: 2026-05-07T00:45:00.738130+08:00
- Base URL: http://127.0.0.1:8031
- Overall status: PASS

## Checks

| Check | Status | Detail |
| --- | --- | --- |
| asset / | PASS | HTTP 200, 8843 bytes |
| asset /app.js | PASS | HTTP 200, 24271 bytes |
| asset /styles.css | PASS | HTTP 200, 12652 bytes |
| api state | PASS | orchestrator=langgraph_default, acceptance=PASS |
| online navigation | PASS | NAVIGATION / EXECUTED / graph=langgraph / trip_plan=True |
| online car control | PASS | CAR_CONTROL / EXECUTED / graph=langgraph / trip_plan=False |
| dangerous block | PASS | CAR_CONTROL / BLOCKED / graph=- / trip_plan=False |
| offline fallback | PASS | CAR_CONTROL / FALLBACK / graph=- / trip_plan=False |
| online friendly error | PASS | HTTP 502, title=没有找到这个目的地 |
| screenshot desktop | PASS | E:\claudeCode\weilaiAgent\reports\browser_qa\desktop.png (84138 bytes) |
| screenshot mobile | PASS | E:\claudeCode\weilaiAgent\reports\browser_qa\mobile.png (29120 bytes) |

## Screenshots

- desktop.png: `E:\claudeCode\weilaiAgent\reports\browser_qa\desktop.png`
- mobile.png: `E:\claudeCode\weilaiAgent\reports\browser_qa\mobile.png`
