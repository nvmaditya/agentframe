from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from agentframe.runtime import ModelMessage
from agentframe.runtime.openai import OpenAICompatibleClient


def test_openai_compatible_client_posts_chat_completions() -> None:
    seen: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            seen["path"] = self.path
            seen["body"] = json.loads(self.rfile.read(length))
            payload = {
                "choices": [{"message": {"content": "hello"}}],
            }
            raw = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *_args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        client = OpenAICompatibleClient(
            base_url=f"http://{host}:{port}/v1",
            api_key="sk-test",
            model="demo",
        )
        response = client.complete([ModelMessage(role="user", content="hi")])
        assert response.content == "hello"
        assert seen["path"] == "/v1/chat/completions"
        assert seen["body"]["model"] == "demo"
        assert seen["body"]["messages"][0]["content"] == "hi"
        assert "temperature" not in seen["body"]
        hot = OpenAICompatibleClient(
            base_url=f"http://{host}:{port}/v1",
            api_key="sk-test",
            model="demo",
            temperature=0,
        )
        hot.complete([ModelMessage(role="user", content="hi")])
        assert seen["body"]["temperature"] == 0
    finally:
        server.shutdown()


def test_openai_compatible_client_surfaces_http_errors() -> None:
    client = OpenAICompatibleClient(base_url="http://example.invalid/v1", api_key="sk", model="demo")
    error = HTTPError("http://example.invalid/v1", 500, "no", hdrs=None, fp=BytesIO(b"boom"))
    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(RuntimeError, match="500"):
            client.complete([ModelMessage(role="user", content="hi")])
