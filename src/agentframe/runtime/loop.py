from __future__ import annotations

import json
from datetime import datetime, timezone
from collections.abc import Iterator
from typing import Any, get_type_hints

from pydantic import ValidationError

from agentframe.contracts import validate_output
from agentframe.core.agent import Agent
from agentframe.core.catalog import AgenticSpec
from agentframe.core.strategy import CodeActStrategy, PredictStrategy
from agentframe.history.event import Event
from agentframe.history.log import EventLog
from agentframe.runtime.context import bind_arguments, static_prefix
from agentframe.runtime.errors import TurnLimitExceeded
from agentframe.runtime.model import ModelClient, ModelMessage
from agentframe.runtime.pause import Paused
from agentframe.runtime.preview import preview
from agentframe.sandbox.executor import Executor
from agentframe.sandbox.result import ExecutionResult


class AgentRuntime:
    def __init__(
        self,
        model: ModelClient,
        executor: Executor,
        events: EventLog,
        *,
        default_agent_id: str | None = None,
    ) -> None:
        self.model = model
        self.executor = executor
        self.events = events
        self.default_agent_id = default_agent_id

    def run(self, agent: Agent, *args: Any, method: str = "run", **kwargs: Any) -> Any:
        return _drain(self.iterate(agent, *args, method=method, **kwargs))

    def iterate(
        self, agent: Agent, *args: Any, method: str = "run", **kwargs: Any
    ) -> Iterator[Paused]:
        spec = type(agent).__agentframe_agentic__.get(method)
        if spec is None:
            if hasattr(agent, method):
                raise TypeError(f"{method!r} is not an agentic method")
            raise AttributeError(f"{type(agent).__name__} has no method {method!r}")
        agent.__runtime__ = self
        agent.events = self.events
        agent_id = self.default_agent_id or f"{type(agent).__name__}-{id(agent):x}"
        self._append("TaskStarted", {"method": method}, agent_id)
        try:
            if isinstance(spec.strategy, PredictStrategy):
                return self._predict(agent, spec, args, kwargs)
            return (yield from self._codeact_iter(agent, spec, args, kwargs))
        finally:
            agent.__runtime__ = None

    def _invoke(self, agent: Agent, spec: AgenticSpec, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        if isinstance(spec.strategy, PredictStrategy):
            return self._predict(agent, spec, args, kwargs)
        return _drain(self._codeact_iter(agent, spec, args, kwargs))

    def _predict(self, agent: Agent, spec: AgenticSpec, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        strategy = spec.strategy
        assert isinstance(strategy, PredictStrategy)
        bound = bind_arguments(spec.fn, args, kwargs)
        agent_id = self._agent_id(agent)
        annotation = get_type_hints(spec.fn).get("return", Any)
        last_error: Exception | None = None
        for _attempt in range(strategy.max_retries + 1):
            messages = self._messages(agent, spec, bound, dynamic_extra="")
            response = self.model.complete(messages)
            self._append("ModelTurn", {"content": response.content}, agent_id)
            try:
                value = _parse_predict(response.content)
                result = validate_output(value, annotation)
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                self._append("ValidationError", {"error": str(exc)}, agent_id)
                continue
            self._append("Termination", {"ok": True}, agent_id)
            return result
        assert last_error is not None
        raise last_error

    def _codeact_iter(
        self, agent: Agent, spec: AgenticSpec, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> Iterator[Paused]:
        strategy = spec.strategy
        assert isinstance(strategy, CodeActStrategy)
        bound = bind_arguments(spec.fn, args, kwargs)
        agent_id = self._agent_id(agent)
        annotation = get_type_hints(spec.fn).get("return", Any)
        namespace: dict[str, Any] = {"self": agent, **bound}
        for name, fn in type(agent).__agentframe_tools__.items():
            namespace[name] = getattr(agent, name)
        box: list[Any] = []

        def return_result(value: Any) -> None:
            box.clear()
            box.append(value)

        namespace["return_result"] = return_result

        for turn in range(strategy.max_turns):
            remaining = strategy.max_turns - turn
            extras = [preview(k, v) for k, v in bound.items()]
            extras.append(f"remaining_turns={remaining}")
            messages = self._messages(agent, spec, bound, dynamic_extra="\n".join(extras))
            response = self.model.complete(messages)
            self._append("ModelTurn", {"content": response.content}, agent_id)
            box.clear()
            result: ExecutionResult = self.executor.execute(response.content, namespace)
            self._append(
                "Execution",
                {
                    "stdout": result.stdout[-500:],
                    "stderr": result.stderr[-500:],
                    "timed_out": result.timed_out,
                    "error": None if result.error is None else repr(result.error),
                },
                agent_id,
            )
            if box:
                try:
                    value = validate_output(box[0], annotation)
                except ValidationError as exc:
                    self._append("ValidationError", {"error": str(exc)}, agent_id)
                    if turn + 1 >= strategy.max_turns:
                        raise TurnLimitExceeded(strategy.max_turns) from exc
                    yield Paused()
                    continue
                self._append("Termination", {"ok": True}, agent_id)
                return value
            observation = result.stdout
            if result.display is not None:
                observation = (observation + "\n" + preview("display", result.display)).strip()
            if result.error is not None:
                observation = (observation + "\n" + _format_error(result.error)).strip()
            self._append("Observation", {"text": observation[:8000]}, agent_id)
            if turn + 1 >= strategy.max_turns:
                raise TurnLimitExceeded(strategy.max_turns)
            yield Paused()
        raise TurnLimitExceeded(strategy.max_turns)

    def _messages(
        self,
        agent: Agent,
        spec: AgenticSpec,
        bound: dict[str, Any],
        dynamic_extra: str,
    ) -> list[ModelMessage]:
        static = static_prefix(agent, spec)
        messages: list[ModelMessage] = [ModelMessage(role="system", content=static)]
        for event in self.events.query(include_collapsed=False):
            if event.type == "TaskStarted":
                continue
            role = "assistant" if event.type == "ModelTurn" else "user"
            content = event.payload.get("content") or event.payload.get("text") or json.dumps(event.payload)
            messages.append(ModelMessage(role=role, content=str(content)))
        dynamic_parts = [preview(name, value) for name, value in vars(agent).items() if not name.startswith("_")]
        if dynamic_extra:
            dynamic_parts.append(dynamic_extra)
        messages.append(ModelMessage(role="user", content="\n".join(dynamic_parts)))
        return messages

    def _append(self, type: str, payload: dict[str, Any], agent_id: str) -> None:
        self.events.append(
            Event(
                type=type,
                payload=payload,
                timestamp=datetime.now(timezone.utc),
                agent_id=agent_id,
            )
        )

    def _agent_id(self, agent: Agent) -> str:
        return self.default_agent_id or f"{type(agent).__name__}-{id(agent):x}"


def _drain(steps: Iterator[Paused]) -> Any:
    try:
        while True:
            next(steps)
    except StopIteration as done:
        return done.value


def _parse_predict(content: str) -> Any:
    return json.loads(content)


def _format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"
