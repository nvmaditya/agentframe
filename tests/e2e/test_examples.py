"""Every documented example is a passing Feature/E2E test."""

from __future__ import annotations

from examples.codeact_live_list import run_example as live_list
from examples.pause_resume import run_example as pause_resume
from examples.predict_classifier import run_example as classify
from examples.validated_termination import run_example as terminate


def test_predict_classifier_example() -> None:
    assert classify() == "ham"


def test_codeact_live_list_example() -> None:
    assert live_list() == 99


def test_validated_termination_example() -> None:
    assert terminate() == "HELLO ADA"


def test_pause_resume_example() -> None:
    assert pause_resume() == "hello"
