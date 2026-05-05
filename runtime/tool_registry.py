class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name: str, handler):
        if not name:
            raise ValueError("tool name is required")
        if not callable(handler):
            raise TypeError("tool handler must be callable")
        self._tools[name] = handler

    def call(self, name: str, payload: dict):
        if name not in self._tools:
            raise KeyError(f"tool not registered: {name}")
        return self._tools[name](payload)

    def list_names(self):
        return sorted(self._tools)
