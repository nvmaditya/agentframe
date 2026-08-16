"""Feature/E2E: scripted CodeAct cell calls a composed worker method."""

from examples.compose_manager import run_example


def test_compose_manager_example() -> None:
    assert run_example() == "HELLO"
