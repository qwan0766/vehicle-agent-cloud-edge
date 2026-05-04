# 网页展示说明

## 1. 定位

网页展示层用于把控制台项目包装成面试可演示的本地可视化应用。它仍然保持 offline 设计，不引入 Flask、FastAPI、Streamlit 或前端框架。

## 2. 运行方式

```bash
python web_demo/server.py
```

如果本机 `python` 命令不可用，可以使用指定 Python 3.8~3.11 解释器运行：

```bash
C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe web_demo/server.py
```

启动后访问：

```text
http://127.0.0.1:8000
```

## 3. 页面结构

- 车辆状态：车速、电量、网络状态、GPS。
- 指令执行：内置场景按钮、自定义指令输入、ONLINE/OFFLINE 切换。
- Agent 调用链：展示 LocalIntentAgent、SafetyAgent、CloudScheduleAgent 等链路。
- 执行结果：展示 request_id、意图、安全等级、执行状态和最终结果。

## 4. 后端接口

```text
GET /api/state
POST /api/run
```

`POST /api/run` 请求示例：

```json
{
  "content": "导航去蔚来中心",
  "user_id": "user_001",
  "network": "ONLINE"
}
```

## 5. 工程思维

网页层没有直接读取 Agent 内部对象，而是通过 `web_demo/app_model.py` 把核心服务输出转换成稳定 JSON。这样做有两个好处：

- 前端只关心展示协议，不关心后端内部类。
- 后续替换 FastAPI、Streamlit 或真实前端框架时，可以复用同一份展示模型。

面试表达：

> 我没有让页面直接耦合各个 Agent，而是增加了一个 Web 展示适配层。它把核心服务的 ExecutionResult 转成 JSON，使 UI、HTTP 服务和核心业务之间保持清晰边界。
