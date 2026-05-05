class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._specs = {}

    def register(self, name: str, handler, spec=None):
        if not name:
            raise ValueError("tool name is required")
        if not callable(handler):
            raise TypeError("tool handler must be callable")
        self._tools[name] = handler
        self._specs[name] = spec

    def call(self, name: str, payload: dict):
        if name not in self._tools:
            raise KeyError(f"tool not registered: {name}")
        spec = self._specs.get(name)
        if spec:
            spec.validate_input(payload)
        output = self._tools[name](payload)
        if spec:
            spec.validate_output(output)
        return output

    def list_names(self):
        return sorted(self._tools)
