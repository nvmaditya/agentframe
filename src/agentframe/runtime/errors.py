class TurnLimitExceeded(RuntimeError):
    def __init__(self, max_turns: int) -> None:
        super().__init__(f"CodeAct exceeded {max_turns} turns without a valid return")
        self.max_turns = max_turns
