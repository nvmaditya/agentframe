"""General helpful agent: tools for math, time, and session notes. Talks via Ollama."""

from __future__ import annotations

import ast
import operator
import sys
from datetime import datetime

from agentframe import Agent, AgentRuntime, CodeActStrategy, TurnLimitExceeded, strategy

try:
    from examples.ollama_runtime import ollama_runtime
except ImportError:  # python examples/ollama_helper.py
    from ollama_runtime import ollama_runtime

_OPS: dict[type, object] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_num(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_num(node.operand))  # type: ignore[operator]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_num(node.left), _eval_num(node.right))  # type: ignore[operator]
    raise ValueError("only numeric + - * / // % ** are allowed")


class Helper(Agent):
    """General assistant. Use tools, then return_result with a short answer."""

    notes: dict = {}

    def now(self) -> str:
        """Current local date and time (ISO, seconds)."""
        return datetime.now().isoformat(timespec="seconds")

    def calculate(self, expression: str) -> float:
        """Evaluate a numeric expression such as '6 * 7' or '17 + 19'."""
        return _eval_num(ast.parse(expression, mode="eval").body)

    def remember(self, key: str, value: str) -> str:
        """Store a fact on this agent for later recall."""
        self.notes[key] = value
        return value

    def recall(self, key: str) -> str:
        """Return a stored fact, or '' if unknown."""
        return str(self.notes.get(key, ""))

    @strategy(CodeActStrategy(max_turns=6))
    def run(self, task: str) -> str:
        """Help with task. Greetings: return_result('Hello! How can I help?'). Tools: self.calculate, self.now, self.remember, self.recall. Always finish with return_result(short_string)."""
        ...


def ask(agent: Helper, task: str, runtime: AgentRuntime | None = None) -> str:
    """One user turn. Fresh log unless a runtime is passed. Never raises TurnLimitExceeded."""
    rt = runtime or ollama_runtime()
    try:
        return rt.run(agent, task)
    except TurnLimitExceeded:
        return "I couldn't finish that. Try a calculation, the time, or a shorter question."


def run_example(task: str = "What is 6 * 7?", runtime: AgentRuntime | None = None) -> str:
    if runtime is not None:
        return runtime.run(Helper(), task)
    last: Exception | None = None
    for _ in range(2):
        try:
            return ollama_runtime().run(Helper(), task)
        except Exception as exc:
            last = exc
    assert last is not None
    raise last


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    agent = Helper()
    if args:
        print(ask(agent, " ".join(args)))
        return
    print("Helper — empty line to quit.")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            return
        print(ask(agent, line))


if __name__ == "__main__":
    main()
