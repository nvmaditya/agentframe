from agentframe.runtime.preview import preview


def test_list_preview_has_length_head_tail_not_middle() -> None:
    data = list(range(100))
    text = preview("data", data)
    assert "len=100" in text
    assert "0" in text and "99" in text
    assert "50" not in text


def test_scalar_repr_when_short() -> None:
    assert "7" in preview("n", 7)
