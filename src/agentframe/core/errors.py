class RuntimeUnboundError(RuntimeError):
    def __init__(self, method: str) -> None:
        super().__init__(f"agentic method {method!r} requires an AgentRuntime")
        self.method = method
