from __future__ import annotations

import copy
import functools
import inspect
from typing import Any, get_type_hints

from agentframe.core.catalog import AgenticSpec, is_ellipsis_body
from agentframe.core.errors import RuntimeUnboundError
from agentframe.core.strategy import CodeActStrategy

RESERVED_FIELDS = frozenset({"events", "__runtime__"})


class _AgenticDescriptor:
    def __init__(self, spec: AgenticSpec) -> None:
        self.spec = spec

    def __get__(self, obj: Any, owner: type | None = None) -> Any:
        if obj is None:
            return self

        @functools.wraps(self.spec.fn)
        def bound(*args: Any, **kwargs: Any) -> Any:
            runtime = getattr(obj, "__runtime__", None)
            if runtime is None:
                raise RuntimeUnboundError(self.spec.name)
            return runtime._invoke(obj, self.spec, args, kwargs)

        return bound


class Agent:
    """Base class: annotated fields are state, method bodies declare kind."""

    __agentframe_tools__: dict[str, Any]
    __agentframe_agentic__: dict[str, AgenticSpec]
    __agentframe_doc__: str | None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        hints = getattr(cls, "__annotations__", {})
        for name in hints:
            if name in RESERVED_FIELDS:
                raise TypeError(f"{name!r} is reserved on Agent")

        tools: dict[str, Any] = {}
        agentic: dict[str, AgenticSpec] = {}
        for name, value in cls.__dict__.items():
            if name.startswith("__") and name.endswith("__"):
                continue
            if not callable(value) or isinstance(value, type):
                continue
            declared = getattr(value, "__agentframe_strategy__", None)
            ellipsis = is_ellipsis_body(value)
            if declared is not None and not ellipsis:
                raise TypeError(f"@strategy cannot decorate a real body ({cls.__name__}.{name})")
            if name.startswith("_"):
                continue
            if ellipsis:
                spec = AgenticSpec(
                    name=name,
                    fn=value,
                    strategy=declared if declared is not None else CodeActStrategy(),
                    doc=inspect.getdoc(value),
                )
                agentic[name] = spec
                setattr(cls, name, _AgenticDescriptor(spec))
            else:
                tools[name] = value
        cls.__agentframe_tools__ = tools
        cls.__agentframe_agentic__ = agentic
        cls.__agentframe_doc__ = inspect.getdoc(cls)

    def __init__(self, **kwargs: Any) -> None:
        hints = {
            name: ann
            for name, ann in get_type_hints(type(self)).items()
            if name not in RESERVED_FIELDS and not name.startswith("_")
        }
        for name in hints:
            if name in kwargs:
                setattr(self, name, kwargs.pop(name))
            elif name in type(self).__dict__:
                setattr(self, name, copy.deepcopy(type(self).__dict__[name]))
            else:
                raise TypeError(f"missing required field {name!r}")
        if kwargs:
            unexpected = ", ".join(sorted(kwargs))
            raise TypeError(f"unexpected field(s): {unexpected}")
        self.__runtime__ = None
        self.events = None
