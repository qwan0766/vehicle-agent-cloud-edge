# 用户画像检索与个性化决策设计

## 1. 设计目标

本阶段将原先的用户画像字典查询升级为可检索的 Profile Retrieval。

目标是让云端 Agent 不只是返回静态用户偏好，而是能把用户长期偏好作为上下文注入路线规划、车控建议和网页展示。

## 2. 当前实现

新增或增强内容：

- `rag/documents.py` 中新增 `PROFILE_DOCUMENTS`。
- `CloudUserProfileAgent` 新增 `retrieve_context(user_id, content)`。
- `CloudUserProfileAgent` 新增 `get_route_preference(user_id, content)`。
- `CloudScheduleAgent` 将用户路线偏好传给 `CloudRoutePlanAgent`。
- `web_demo/app_model.py` 将用户画像召回加入 `rag_context`。

## 3. 数据流

```text
用户输入 + user_id
  -> CloudUserProfileAgent.retrieve_context
  -> PROFILE_DOCUMENTS
  -> route_preference
  -> CloudRoutePlanAgent.plan
  -> 个性化路线结果
```

示例：

```text
user_001 + 导航去蔚来中心
  -> 召回：user_001：温度24℃，座椅加热自动开启，路线偏好高速
  -> 路线规划：长途优先高速路线，结合用户路线偏好高速
```

## 4. 网页展示

网页的“RAG 召回知识”区域现在会展示三类上下文：

- 本地意图识别。
- 用户画像召回。
- 云端路线规划。

这能让面试官直接看到系统为什么做出当前决策，而不是只看到一个最终字符串。

## 5. 工程取舍

当前仍然使用本地检索而不是数据库，原因是：

- 保持 offline 可运行。
- 避免环境依赖冲突。
- 先验证用户画像作为上下文注入决策链路的设计。
- 后续可以平滑替换为真实用户画像库或向量库。

面试表达：

> 我把用户画像也做成了可检索文档，而不是只用 user_id 查字典。这样用户偏好可以和当前指令一起参与召回，并作为上下文影响云端路线规划。后续可以把本地 profile 文档替换为真实用户画像库或向量检索服务。

## 6. 后续扩展

可以继续增强：

- 多用户切换。
- 用户偏好更新与数据闭环。
- 将行程结束后的行为写回 profile。
- 区分长期偏好和临时偏好。
- 加入隐私脱敏与最小化使用原则。
