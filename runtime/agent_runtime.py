from time import perf_counter


class AgentRuntime:
    def __init__(self):
        self._trace = []

    def reset(self):
        self._trace = []

    def call_tool(self, registry, tool_name: str, payload: dict):
        started = perf_counter()
        output = registry.call(tool_name, payload)
        duration_ms = round((perf_counter() - started) * 1000, 3)
        self._trace.append(
            {
                "tool_name": tool_name,
                "input": dict(payload),
                "output": output,
                "duration_ms": duration_ms,
            }
        )
        return output

    def snapshot(self):
        return [dict(item) for item in self._trace]
