from agentframe.runtime.preview import preview


def test_list_preview_has_length_head_tail_not_middle() -> None:
    data = list(range(100))
    text = preview("data", data)
    assert "len=100" in text
    assert "0" in text and "99" in text
    assert "50" not in text


def test_scalar_repr_when_short() -> None:
    assert "7" in preview("n", 7)


def test_short_sequence_has_no_tail_slice() -> None:
    text = preview("xs", [1, 2])
    assert "[-5:]" not in text
    assert "len=2" in text


def test_long_scalar_uses_head_form() -> None:
    text = preview("blob", "x" * 2000)
    assert "len=2000" in text
    assert "head=" in text


def test_preview_honours_cap() -> None:
    text = preview("data", list(range(100)), cap=40)
    assert text.endswith("...")
    assert len(text) <= 40
