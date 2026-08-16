from agentframe.mcp.slug import slugify_tools


def test_slugify_hyphens_digits_and_collisions() -> None:
    mapping = slugify_tools(["list-issues", "list_issues", "123go", "ok"])
    assert mapping["list-issues"] == "list_issues"
    assert mapping["list_issues"] == "list_issues_2"
    assert mapping["123go"] == "t_123go"
    assert mapping["ok"] == "ok"
