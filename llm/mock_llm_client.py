class MockLLMClient:
    provider_name = "mock"

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        context = context or {}
        route_hint = context.get("route_hint") or context.get("route") or "根据当前上下文规划路线"
        map_route = context.get("map_route", "")
        preference = context.get("route_preference", "")
        parts = [f"LLM决策：{route_hint}"]
        if preference:
            parts.append(f"偏好{preference}")
        if map_route:
            parts.append(str(map_route))
        return "，".join(parts)
