from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from agentframe.mcp.errors import McpError
from agentframe.mcp.rpc import decode_response, encode_request


class StdioTransport:
    """Spawn a local MCP server and speak JSON-RPC with Content-Length framing."""

    def __init__(
        self,
        command: str,
        args: tuple[str, ...] = (),
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> None:
        self.command = command
        self.args = args
        self.env = env
        self.cwd = cwd
        self._proc: subprocess.Popen[bytes] | None = None
        self._next_id = 1

    def open(self) -> None:
        merged = os.environ.copy()
        if self.env:
            merged.update(self.env)
        self._proc = subprocess.Popen(
            [self.command, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=merged,
        )

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    def request(self, method: str, params: dict[str, Any]) -> Any:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise McpError("stdio transport is closed")
        if method.startswith("notifications/"):
            self._write(encode_request(None, method, params))
            return None
        req_id = self._next_id
        self._next_id += 1
        self._write(encode_request(req_id, method, params))
        message = self._read()
        return decode_response(message)

    def _write(self, message: dict[str, Any]) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        raw = json.dumps(message).encode("utf-8")
        header = f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii")
        try:
            self._proc.stdin.write(header + raw)
            self._proc.stdin.flush()
        except OSError as exc:
            raise McpError(f"stdio write failed: {exc}") from exc

    def _read(self) -> dict[str, Any]:
        assert self._proc is not None and self._proc.stdout is not None
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = self._proc.stdout.read(1)
            if not chunk:
                err = ""
                if self._proc.stderr is not None:
                    err = self._proc.stderr.read().decode("utf-8", errors="replace")
                raise McpError(f"stdio EOF while reading headers {err}")
            header += chunk
        header_text, _sep, rest = header.partition(b"\r\n\r\n")
        length = 0
        for line in header_text.decode("ascii", errors="replace").split("\r\n"):
            if line.lower().startswith("content-length:"):
                length = int(line.split(":", 1)[1].strip())
        body = rest
        while len(body) < length:
            chunk = self._proc.stdout.read(length - len(body))
            if not chunk:
                raise McpError("stdio EOF while reading body")
            body += chunk
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise McpError(f"invalid JSON-RPC from stdio: {exc}") from exc
