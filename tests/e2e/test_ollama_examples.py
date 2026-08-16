"""Live Ollama examples. Skip when the daemon is not reachable (CI)."""

from __future__ import annotations

import os
import urllib.error
import urllib.request

import pytest

from examples.ollama_greeter import run_example as greet
from examples.ollama_helper import run_example as help_with
from examples.ollama_runtime import clean_cell, ensure_return, strip_fences
from examples.ollama_team import run_example as team


def _ollama_up() -> bool:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    if host.endswith("/v1"):
        host = host[:-3]
    try:
        urllib.request.urlopen(f"{host}/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


_skip_live = pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true" or not _ollama_up(),
    reason="Ollama is not running (or this is CI)",
)


def test_strip_fences_unwraps_python_block() -> None:
    raw = "```python\nreturn_result(self.shout('hello ' + who))\n```"
    assert strip_fences(raw) == "return_result(self.shout('hello ' + who))"


def test_clean_cell_drops_object_repr_echo() -> None:
    raw = (
        "events = InMemoryEventLog(<agentframe.history.memory.InMemoryEventLog object at 0xABC>)\n"
        "events.log(text)\n"
        "return_result(self.worker.shout(task))"
    )
    assert clean_cell(raw) == "return_result(self.worker.shout(task))"


def test_ensure_return_wraps_a_greeting() -> None:
    assert ensure_return("Hi") == "return_result('Hi')"
    assert clean_cell("task = str('hi')\nHi there!") == "return_result('Hi there!')"
    assert ensure_return('return_result("Hi")') == 'return_result("Hi")'


@_skip_live
@pytest.mark.ollama
def test_ollama_greeter() -> None:
    assert greet() == "HELLO ADA"


@_skip_live
@pytest.mark.ollama
def test_ollama_team() -> None:
    assert team() == "HELLO"


@_skip_live
@pytest.mark.ollama
def test_ollama_helper() -> None:
    assert "42" in help_with("What is 6 * 7?")
