# 本地 RAG 检索设计

## 1. 设计目标

本阶段将原先的“硬编码 RAG 模拟”升级为一个可解释的本地检索模块。

目标不是直接接入向量数据库，而是先建立稳定边界：

```text
Agent -> Retriever -> Documents -> RetrievalResult
```

这样后续无论替换为 BM25、embedding、FAISS 还是 Milvus，上层 Agent 都不需要大改。

## 2. 当前实现

新增模块：

- `rag/documents.py`：定义检索文档、意图文档、路线知识文档。
- `rag/simple_retriever.py`：实现无依赖关键词评分检索。

核心数据结构：

```text
RetrievalDocument
  - doc_id
  - text
  - keywords
  - metadata

RetrievalResult
  - document
  - score
  - matched_keywords
```

当前评分逻辑：

- 精确子串命中：高分。
- keyword 命中：按关键词加分。
- 中文字符重叠：作为轻量兜底。
- 返回 top-k 结果。

## 3. 已接入 Agent

### 3.1 LocalIntentAgent

原先逻辑：

```text
直接从 INTENT_KNOWLEDGE 字典匹配
```

当前逻辑：

```text
精确匹配
  -> SimpleRetriever 检索相似表达
  -> 危险关键词归类为 CAR_CONTROL
  -> UNKNOWN
```

示例：

```text
帮我导航到蔚来中心 -> NAVIGATION
```

这说明系统不再只支持完全相同的输入，也能处理轻微变化的自然语言表达。

### 3.2 CloudRoutePlanAgent

原先逻辑：

```text
if "电量低" in content:
    返回补能建议
else:
    返回高速优先
```

当前逻辑：

```text
使用 SimpleRetriever 从 ROUTE_DOCUMENTS 召回路线知识
  -> 取 top-1 作为路线规划依据
  -> 无召回时使用默认高速策略
```

示例：

```text
电量低，需要补能 -> 电量低于20%建议前往换电站
```

## 4. 网页展示增强

网页 API 现在会返回：

```json
{
  "rag_context": [
    {
      "stage": "本地意图识别",
      "doc_id": "intent_nav_nio_center",
      "text": "导航去蔚来中心",
      "score": 6,
      "matched_keywords": ["导航", "蔚来中心"]
    }
  ]
}
```

页面新增“RAG 召回知识”区域，展示：

- 召回阶段。
- 文档内容。
- 分数。
- 命中关键词。

这样面试演示时可以直接说明 Agent 的回答依据，而不是只展示最终结果。

## 5. 工程取舍

当前没有引入向量数据库，原因是：

- 项目定位仍然是 offline。
- 目标是证明 RAG 架构位置和接口边界。
- 关键词检索可解释、无依赖、易测试。
- 对应届生作品来说，可运行性和可讲清楚比堆复杂组件更重要。

面试表达：

> 我先抽象了 Retriever，而不是直接接向量库。当前实现用关键词评分模拟 RAG 召回，能展示检索依据、分数和命中关键词。后续只需要替换 Retriever 底层实现，就可以升级为 BM25、embedding、FAISS 或 Milvus。

## 6. 后续升级路径

推荐升级顺序：

```text
SimpleRetriever
  -> BM25 / TF-IDF
  -> embedding 模型
  -> FAISS 本地向量库
  -> Milvus / 云端向量检索
  -> LLM + tool calling / LangGraph 编排
```

保持不变的上层接口：

```text
retriever.search(query, top_k)
```

这就是当前阶段最重要的工程价值：先把边界设计好，再逐步替换能力实现。
