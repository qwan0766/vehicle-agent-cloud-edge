# Web QA Report

- Generated at: 2026-05-08T21:26:19.311062+08:00
- Base URL: http://127.0.0.1:8031
- Overall status: PASS

## Checks

| Check | Status | Detail |
| --- | --- | --- |
| asset / | PASS | HTTP 200, 10805 bytes |
| asset /app.js | PASS | HTTP 200, 2915 bytes |
| asset /styles.css | PASS | HTTP 200, 17130 bytes |
| asset /js/api.js | PASS | HTTP 200, 1707 bytes |
| asset /js/events.js | PASS | HTTP 200, 7008 bytes |
| asset /js/renderers/demo.js | PASS | HTTP 200, 2957 bytes |
| asset /js/renderers/result.js | PASS | HTTP 200, 9194 bytes |
| api state | PASS | orchestrator=langgraph_default, acceptance=PASS, demo_steps=5 |
| online navigation | PASS | NAVIGATION / EXECUTED / graph=langgraph / trip_plan=True |
| online car control | PASS | CAR_CONTROL / EXECUTED / graph=langgraph / trip_plan=False |
| dangerous block | PASS | CAR_CONTROL / BLOCKED / graph=- / trip_plan=False |
| offline fallback | PASS | CAR_CONTROL / FALLBACK / graph=- / trip_plan=False |
| clarification normal state | PASS | 北京 -> NEEDS_CLARIFICATION |
| demo online_navigation | PASS | 正常导航端云协同: NAVIGATION / EXECUTED |
| demo fuzzy_destination_clarification | PASS | 模糊目的地澄清: NAVIGATION / NEEDS_CLARIFICATION |
| demo highway_speed_confirmation | PASS | 高速速度请求确认: CAR_CONTROL / NEEDS_DRIVER_CONFIRMATION |
| demo urban_speed_block | PASS | 城市超限危险拦截: CAR_CONTROL / BLOCKED |
| demo low_battery_energy_policy | PASS | 低电量状态与能源策略: NAVIGATION / NEEDS_CHARGE_CONFIRMATION |
| confirm destination pending | PASS | destination_clarification -> EXECUTED |
| screenshot desktop | PASS | E:\claudeCode\weilaiAgent\reports\browser_qa\desktop.png (86565 bytes) |
| screenshot mobile | PASS | E:\claudeCode\weilaiAgent\reports\browser_qa\mobile.png (28389 bytes) |

## Screenshots

- desktop.png: `E:\claudeCode\weilaiAgent\reports\browser_qa\desktop.png`
  ![desktop](E:/claudeCode/weilaiAgent/reports/browser_qa/desktop.png)
- mobile.png: `E:\claudeCode\weilaiAgent\reports\browser_qa\mobile.png`
  ![mobile](E:/claudeCode/weilaiAgent/reports/browser_qa/mobile.png)
