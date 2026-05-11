---
doc_id: navigation_offline_fallback
topic: navigation
keywords: 断网, 离线导航, 网络, 本地导航, 端云协同, 导航兜底
---

# 离线导航与断网兜底

当车辆网络状态为 OFFLINE 时，车端系统不能调用云端地图、云端 LLM 或外部生态接口。

离线导航应使用本地可用的地图缓存、常用地点、历史目的地和本地意图 Agent 的上下文判断。对于目的地不明确、候选地点过多或没有本地缓存的情况，应进入 NEEDS_CLARIFICATION 或 FALLBACK 状态，而不是伪造云端路线结果。

网络恢复后，系统可以重新进入端云协同链路，用云端路线规划和实时生态数据更新结果。
