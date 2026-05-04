# 系统架构说明

## 1. 三层架构

本项目采用端云协同三层架构：

- 车载执行层：负责本地意图识别、安全拦截、车控执行、离线导航。
- 端云通信层：通过统一 `Message` 协议描述请求，模拟端云报文。
- 云端决策层：负责用户画像、外部生态、路线规划和多 Agent 调度。

## 2. Agent 调用链

```text
用户输入
  -> LocalIntentAgent
  -> SafetyAgent
  -> VehicleCoreService
  -> ONLINE: CloudScheduleAgent
       -> CloudUserProfileAgent
       -> CloudEcologyAgent
       -> CloudRoutePlanAgent
  -> OFFLINE: CarControlAgent / NavAgent / local fallback
```

## 3. 核心数据流

```text
user_input
  -> command_type
  -> safety_level
  -> Message(request_id, user_id, command_type, safety, content, network)
  -> ExecutionResult(status, output, message)
```

`Message` 是系统的统一协议。车端、云端、测试和日志都围绕它协作。

## 4. 安全优先级

安全校验优先于任何执行路径。即使指令被识别为 `CAR_CONTROL`，只要 `SafetyAgent` 判断为 `DANGEROUS`，系统就返回 `BLOCKED`，不会进入车控执行或云端执行。

## 5. 断网兜底

当网络状态为 `OFFLINE` 时，系统不访问云端调度，而是直接进入车端本地能力：

- 车控指令：由 `CarControlAgent` 执行。
- 导航指令：由 `NavAgent` 执行。
- 充电规划：返回本地知识库建议。
- 个性化：返回本地默认偏好。

## 6. 后续扩展点

- 将 `LocalIntentAgent` 的规则匹配替换为轻量 embedding 模型。
- 将 `CloudRoutePlanAgent` 的列表检索替换为 FAISS 或 Milvus。
- 将 `CloudEcologyAgent` 替换为 Open-Meteo、OpenChargeMap 或地图 API。
- 为 `VehicleCoreService` 增加链路日志、埋点和数据闭环记录。
