"""IsolatedExecutor runs cells outside the agent process and default-denies FS/net."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from agentframe.sandbox import ExecutionTimeout, IsolatedExecutor, gvisor_available


@pytest.fixture
def exe() -> IsolatedExecutor:
    return IsolatedExecutor(timeout_seconds=2.0)


def test_isolated_execute_does_not_raise_on_cell_error(exe: IsolatedExecutor) -> None:
    result = exe.execute("1/0", {})
    assert result.error is not None
    assert isinstance(result.error, ZeroDivisionError)


def test_isolated_cannot_read_host_path(exe: IsolatedExecutor, tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("LEAK")
    result = exe.execute(f"open({str(secret)!r}).read()", {})
    assert result.error is not None
    dumped = (result.stdout or "") + str(result.display)
    assert "LEAK" not in dumped


def test_isolated_cannot_write_host_path(exe: IsolatedExecutor, tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("safe")
    result = exe.execute(f"open({str(secret)!r}, 'w').write('pwned')", {})
    assert result.error is not None
    assert secret.read_text() == "safe"


_PATH_ESCAPE = """
seen = []
def walk(cls, depth=0):
    if depth > 8:
        return
    try:
        kids = getattr(cls, "__subclasses__")()
    except Exception:
        return
    for c in kids:
        seen.append(c)
        walk(c, depth + 1)
walk(object)
found = None
for c in seen:
    try:
        if getattr(c, "__name__", "") == "Path" and hasattr(c, "write_text"):
            found = c
            break
    except Exception:
        pass
if found is None:
    raise RuntimeError("no Path")
p = found({path!r})
p.write_text("pwned")
p.read_text()
"""

_FILEIO_ESCAPE = """
seen = []
def walk(cls, depth=0):
    if depth > 8:
        return
    try:
        kids = getattr(cls, "__subclasses__")()
    except Exception:
        return
    for c in kids:
        seen.append(c)
        walk(c, depth + 1)
walk(object)
found = None
for c in seen:
    if getattr(c, "__name__", "") in ("FileIO", "BufferedWriter"):
        found = c
        break
if found is None:
    raise RuntimeError("no FileIO")
f = found({path!r}, "w")
f.write(b"pwned")
f.close()
"pwned"
"""

_SOCKET_ESCAPE = """
seen = []
def walk(cls, depth=0):
    if depth > 8:
        return
    try:
        kids = getattr(cls, "__subclasses__")()
    except Exception:
        return
    for c in kids:
        seen.append(c)
        walk(c, depth + 1)
walk(object)
sock = None
for c in seen:
    if getattr(c, "__name__", "") == "socket" and callable(c):
        sock = c
        break
if sock is None:
    raise RuntimeError("no socket")
s = sock()
s.settimeout(2)
s.connect(("1.1.1.1", 80))
s.close()
"connected"
"""


def test_isolated_cannot_write_via_recovered_path(exe: IsolatedExecutor, tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("safe")
    result = exe.execute(_PATH_ESCAPE.format(path=str(secret)), {})
    assert result.error is not None
    assert result.display != "pwned"
    assert secret.read_text() == "safe"


def test_isolated_cannot_write_via_recovered_fileio(exe: IsolatedExecutor, tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("safe")
    result = exe.execute(_FILEIO_ESCAPE.format(path=str(secret)), {})
    assert result.error is not None
    assert result.display != "pwned"
    assert secret.read_text() == "safe"


def test_isolated_cannot_connect_via_recovered_socket(exe: IsolatedExecutor) -> None:
    result = exe.execute(_SOCKET_ESCAPE, {})
    assert result.error is not None
    assert result.display != "connected"


def test_isolated_cannot_open_network(exe: IsolatedExecutor) -> None:
    for source in (
        "import socket",
        "import urllib.request",
        "__import__('socket')",
        "import socket; socket.create_connection(('1.1.1.1', 80), 1)",
    ):
        result = exe.execute(source, {})
        assert result.error is not None, source


def test_isolated_hang_times_out() -> None:
    exe = IsolatedExecutor(timeout_seconds=0.3)
    result = exe.execute("while True:\n    pass", {})
    assert result.timed_out is True
    assert isinstance(result.error, ExecutionTimeout)


def test_gvisor_flag_tracks_runsc() -> None:
    assert IsolatedExecutor().use_gvisor is gvisor_available()


def test_isolated_skips_non_jsonable_namespace(exe: IsolatedExecutor) -> None:
    result = exe.execute("print(x)", {"x": 1, "fn": lambda: None})
    assert result.error is None
    assert "1" in result.stdout


def test_isolated_worker_crash_is_result_not_raise() -> None:
    crashed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="boom")
    with patch("agentframe.sandbox.isolated.subprocess.run", return_value=crashed):
        result = IsolatedExecutor(use_gvisor=False).execute("1", {})
    assert result.error is not None
    assert "boom" in str(result.error)


def test_isolated_parent_timeout_is_result() -> None:
    with patch(
        "agentframe.sandbox.isolated.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="worker", timeout=1),
    ):
        result = IsolatedExecutor(use_gvisor=False, timeout_seconds=0.1).execute("1", {})
    assert result.timed_out is True
    assert isinstance(result.error, ExecutionTimeout)


def test_isolated_prefixes_runsc_when_requested() -> None:
    seen: dict = {}

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        seen["cmd"] = cmd
        body = '{"stdout":"","stderr":"","display":null,"error_type":null,"error_msg":null,"timed_out":false}'
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=body, stderr="")

    with (
        patch("agentframe.sandbox.isolated.shutil.which", return_value="runsc"),
        patch("agentframe.sandbox.isolated.subprocess.run", side_effect=fake_run),
    ):
        IsolatedExecutor(use_gvisor=True).execute("1", {})
    assert seen["cmd"][0] == "runsc"
    assert "--network=none" in seen["cmd"]


def test_gvisor_available_false_when_runsc_missing() -> None:
    with patch("agentframe.sandbox.isolated.shutil.which", return_value=None):
        assert gvisor_available() is False


def test_isolated_non_json_stdout_is_result() -> None:
    junk = subprocess.CompletedProcess(args=[], returncode=0, stdout="not-json", stderr="")
    with patch("agentframe.sandbox.isolated.subprocess.run", return_value=junk):
        result = IsolatedExecutor(use_gvisor=False).execute("1", {})
    assert result.error is not None


def test_isolated_does_not_share_object_identity(exe: IsolatedExecutor) -> None:
    data = [1, 2, 3]
    result = exe.execute("data.append(4)\ndata", {"data": data})
    assert data == [1, 2, 3]
    if result.error is None and isinstance(result.display, list):
        assert result.display is not data
