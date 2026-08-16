from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agentframe.contracts import validate_output
from agentframe.mcp.errors import McpError
from agentframe.mcp.result import McpResult
from agentframe.mcp.slug import slugify_tools
from agentframe.mcp.transport import McpTransport


class McpClient:
    """Consume one MCP server as an object. Tools become methods after connect()."""

    def __init__(self, transport: McpTransport) -> None:
        self._transport = transport
        self._connected = False
        self._tools: dict[str, str] = {}  # python name -> original name
        self._schemas: dict[str, dict[str, Any]] = {}

    def connect(self) -> None:
        self._transport.open()
        try:
            self._transport.request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "agentframe", "version": "0.1.0"},
                },
            )
            self._transport.request("notifications/initialized", {})
            listed = self._transport.request("tools/list", {}) or {}
            tools = listed.get("tools") or []
            originals = [str(item["name"]) for item in tools]
            slugs = slugify_tools(originals)
            self._tools = {slug: original for original, slug in slugs.items()}
            schemas = {item["name"]: item.get("inputSchema") or {} for item in tools}
            for slug, original in self._tools.items():
                self._schemas[slug] = schemas.get(original, {})
                setattr(self, slug, self._bind_tool(slug, original))
        except McpError:
            self._transport.close()
            raise
        except Exception as exc:
            self._transport.close()
            raise McpError(f"handshake failed: {exc}") from exc
        self._connected = True

    def close(self) -> None:
        self._transport.close()
        self._connected = False

    def __enter__(self) -> McpClient:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def list_tools(self) -> list[str]:
        return list(self._tools)

    def list_resources(self) -> list[str]:
        payload = self._transport.request("resources/list", {}) or {}
        return [str(item["uri"]) for item in payload.get("resources") or []]

    def read_resource(self, uri: str) -> McpResult:
        payload = self._transport.request("resources/read", {"uri": uri}) or {}
        return _result_from_contents(payload.get("contents") or [])

    def get_prompt(self, name: str, **arguments: Any) -> str:
        payload = self._transport.request(
            "prompts/get",
            {"name": name, "arguments": arguments},
        ) or {}
        texts: list[str] = []
        for message in payload.get("messages") or []:
            content = message.get("content")
            if isinstance(content, dict) and content.get("text"):
                texts.append(str(content["text"]))
            elif isinstance(content, str):
                texts.append(content)
        return "".join(texts)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        raise McpError(f"unknown tool {name!r}")

    def _bind_tool(self, slug: str, original: str) -> Any:
        schema = self._schemas.get(slug) or {}

        def tool(**kwargs: Any) -> McpResult:
            if schema:
                try:
                    validate_output(kwargs, schema)
                except (ValidationError, TypeError, ValueError) as exc:
                    raise McpError(f"invalid arguments for {original}: {exc}") from exc
            raw = self._transport.request(
                "tools/call",
                {"name": original, "arguments": kwargs},
            ) or {}
            if raw.get("isError"):
                raise McpError(_text_from_content(raw.get("content") or []) or "tools/call isError")
            return _result_from_call(raw)

        tool.__name__ = slug
        tool.__doc__ = original
        tool.__tool_schema__ = schema  # type: ignore[attr-defined]
        return tool


def _text_from_content(parts: list[Any]) -> str:
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            texts.append(str(part["text"]))
        elif isinstance(part, str):
            texts.append(part)
    return "".join(texts)


def _result_from_call(raw: dict[str, Any]) -> McpResult:
    content = list(raw.get("content") or [])
    return McpResult(text=_text_from_content(content), content=content, is_error=False)


def _result_from_contents(contents: list[Any]) -> McpResult:
    texts: list[str] = []
    for item in contents:
        if isinstance(item, dict) and item.get("text"):
            texts.append(str(item["text"]))
    return McpResult(text="".join(texts), content=list(contents), is_error=False)
