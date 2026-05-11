---
doc_id: navigation_destination_clarification
topic: navigation
keywords: 模糊目的地, 候选地点, 目的地确认, POI, 城市, 商圈, 门店, 地址
---

# 模糊目的地澄清策略

用户只说“去北京”“去最漂亮的地方”“去老地方”时，导航意图可能明确，但目的地槽位不完整。

如果目的地只有城市级信息、主观描述、泛称或候选 POI 过多，系统应进入 NEEDS_CLARIFICATION，提示用户补充城市、区县、商圈、门店名或完整地址。

只有当用户输入匹配常用地点、历史高频地点或唯一高置信 POI 时，系统才可以跳过澄清直接规划路线。
