from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


class WidgetNotFound(LookupError):
    """Raised when a widget path is not present in the live state file."""


class MissingTool(RuntimeError):
    """Raised when an external command such as xdotool is unavailable."""


class MissingDisplay(RuntimeError):
    """Raised when no X11 DISPLAY is configured for replay."""


class XdotoolError(RuntimeError):
    """Raised when xdotool fails to send or inspect X11 input."""


class MotifApp:
    """Runtime harness used by generated tests.

    The harness launches the application with the Xt tap hook active, reads the
    live widget state file, and uses xdotool to send X11 input.
    """

    def __init__(
        self,
        argv: list[str],
        *,
        tap_so: str | None = None,
        timeout: float = 10.0,
        keep_artifacts: bool = False,
    ):
        self.argv = argv
        self.tap_so = tap_so or os.environ.get("MOTIF_TAP_SO", "./c/libxttap.so")
        self.timeout = timeout
        self.keep_artifacts = keep_artifacts

        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        if keep_artifacts:
            self.session_dir = Path(tempfile.mkdtemp(prefix="motif-test-"))
        else:
            self._tmp = tempfile.TemporaryDirectory(prefix="motif-test-")
            self.session_dir = Path(self._tmp.name)

        self.state_file = self.session_dir / "latest-state.json"
        self.widget_log = self.session_dir / "widgets.jsonl"
        self.stdout_file = self.session_dir / "stdout.log"
        self.stderr_file = self.session_dir / "stderr.log"
        self.proc: subprocess.Popen[str] | None = None
        self._stdout_handle: Any | None = None
        self._stderr_handle: Any | None = None

    def __enter__(self) -> "MotifApp":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self.capture_diagnostics("failure")
        self.stop()
        if self._tmp is not None:
            self._tmp.cleanup()

    def start(self) -> None:
        self._require_display()
        self._require_tool("xdotool")

        env = os.environ.copy()
        env["MOTIF_TAP_STATE"] = str(self.state_file)
        env["MOTIF_TAP_LOG"] = str(self.widget_log)

        if self.tap_so:
            existing_preload = env.get("LD_PRELOAD", "")
            env["LD_PRELOAD"] = (
                f"{self.tap_so}:{existing_preload}" if existing_preload else self.tap_so
            )

        self._stdout_handle = self.stdout_file.open("w", encoding="utf-8")
        self._stderr_handle = self.stderr_file.open("w", encoding="utf-8")

        try:
            self.proc = subprocess.Popen(
                self.argv,
                env=env,
                text=True,
                stdout=self._stdout_handle,
                stderr=self._stderr_handle,
            )
            self._wait_for_state_file()
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)

        if self._stdout_handle is not None:
            self._stdout_handle.close()
            self._stdout_handle = None
        if self._stderr_handle is not None:
            self._stderr_handle.close()
            self._stderr_handle = None

    def _require_tool(self, name: str) -> None:
        if shutil.which(name) is None:
            raise MissingTool(f"Required command not found in PATH: {name}")

    def _require_display(self) -> None:
        if not os.environ.get("DISPLAY"):
            raise MissingDisplay("DISPLAY is not set; MotifApp replay requires an X11 display")

    def _xdotool(self, *args: object) -> str:
        command = ["xdotool", *map(str, args)]
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            self.capture_diagnostics("xdotool_failed")
            raise XdotoolError(
                "xdotool failed: "
                f"command={command!r} returncode={result.returncode} "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )
        return result.stdout

    def _wait_for_state_file(self) -> None:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self.state_file.exists() and self.state_file.stat().st_size > 0:
                return
            if self.proc and self.proc.poll() is not None:
                raise RuntimeError(f"Application exited before Xt state appeared: {self.argv!r}")
            time.sleep(0.05)
        raise TimeoutError(f"Xt hook did not create {self.state_file}")

    def _load_state(self) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception as exc:
                last_error = exc
                time.sleep(0.05)
        raise RuntimeError(f"Could not read live widget state: {last_error}")

    def widgets(self) -> list[dict[str, Any]]:
        return list(self._load_state().get("widgets", []))

    def widget(self, path: str) -> dict[str, Any]:
        for widget in self.widgets():
            if widget.get("path") == path:
                return widget
        raise WidgetNotFound(path)

    def wait_for_widget(self, path: str, timeout: float | None = None) -> dict[str, Any]:
        deadline = time.monotonic() + (timeout or self.timeout)
        last_error: Exception | None = None

        while time.monotonic() < deadline:
            try:
                widget = self.widget(path)
                if (
                    widget.get("managed", True)
                    and widget.get("sensitive", True)
                    and widget.get("realized", True)
                    and int(widget.get("width", 0)) > 0
                    and int(widget.get("height", 0)) > 0
                ):
                    return widget
            except Exception as exc:
                last_error = exc
            time.sleep(0.05)

        self.capture_diagnostics("wait_for_widget_failed")
        raise TimeoutError(f"Timed out waiting for widget {path!r}: {last_error}")

    def click(self, path: str, *, button: int = 1) -> None:
        widget = self.wait_for_widget(path)
        x = int(widget["root_x"]) + int(widget["width"]) // 2
        y = int(widget["root_y"]) + int(widget["height"]) // 2
        self._xdotool("mousemove", x, y, "click", button)

    def click_relative(self, path: str, x: int, y: int, *, button: int = 1) -> None:
        widget = self.wait_for_widget(path)
        root_x = int(widget["root_x"]) + int(x)
        root_y = int(widget["root_y"]) + int(y)
        self._xdotool("mousemove", root_x, root_y, "click", button)

    def click_root(self, x: int, y: int, *, button: int = 1) -> None:
        self._xdotool("mousemove", x, y, "click", button)

    def press(self, key: str) -> None:
        self._xdotool("key", key)

    def type_text(self, text: str, *, delay_ms: int = 5) -> None:
        self._xdotool("type", "--delay", delay_ms, text)

    def wait_for_idle(self, seconds: float = 0.2) -> None:
        time.sleep(seconds)

    def wait_until(self, description: str, predicate, timeout: float | None = None) -> object:
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        last_error: Exception | None = None

        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value:
                    return value
            except Exception as exc:
                last_error = exc
            time.sleep(0.05)

        self.capture_diagnostics("wait_until_failed")
        detail = f": {last_error}" if last_error else ""
        raise TimeoutError(f"Timed out waiting for {description}{detail}")

    def wait_for_window(self, title: str, timeout: float | None = None) -> None:
        deadline = time.monotonic() + (timeout or self.timeout)
        while time.monotonic() < deadline:
            result = subprocess.run(
                ["xdotool", "search", "--name", title],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0 and result.stdout.strip():
                return
            time.sleep(0.1)
        self.capture_diagnostics("wait_for_window_failed")
        raise TimeoutError(f"Timed out waiting for window title {title!r}")

    def file_exists(self, path: str | Path) -> bool:
        return Path(path).exists()

    def capture_diagnostics(self, label: str) -> Path:
        base = self.session_dir / label
        base.mkdir(parents=True, exist_ok=True)

        if self._stdout_handle is not None:
            self._stdout_handle.flush()
        if self._stderr_handle is not None:
            self._stderr_handle.flush()

        if self.state_file.exists():
            (base / "latest-state.json").write_text(
                self.state_file.read_text(encoding="utf-8"), encoding="utf-8"
            )
        if self.widget_log.exists():
            (base / "widgets.jsonl").write_text(
                self.widget_log.read_text(encoding="utf-8"), encoding="utf-8"
            )
        if self.stdout_file.exists():
            (base / "stdout.log").write_text(
                self.stdout_file.read_text(encoding="utf-8"), encoding="utf-8"
            )
        if self.stderr_file.exists():
            (base / "stderr.log").write_text(
                self.stderr_file.read_text(encoding="utf-8"), encoding="utf-8"
            )

        for command, out_name in [
            (["xwininfo", "-root", "-tree"], "xwininfo-tree.txt"),
            (["xdotool", "search", "--onlyvisible", "--name", "."], "visible-windows.txt"),
        ]:
            if shutil.which(command[0]) is None:
                continue
            with (base / out_name).open("w", encoding="utf-8") as out:
                subprocess.run(
                    command, text=True, stdout=out, stderr=subprocess.STDOUT, check=False
                )

        if shutil.which("xwd") is not None:
            subprocess.run(["xwd", "-root", "-out", str(base / "screen.xwd")], check=False)

        return base
