import subprocess
from pathlib import Path

import pytest

from motiftap.harness import MissingDisplay, MotifApp, XdotoolError


def test_keep_artifacts_uses_persistent_session_directory():
    app = MotifApp(["/bin/true"], keep_artifacts=True)
    session_dir = app.session_dir

    assert session_dir.exists()
    assert app._tmp is None

    app.__exit__(None, None, None)

    assert session_dir.exists()

    # Clean up the directory created by this unit test. Runtime users who pass
    # keep_artifacts=True keep the path for inspection after a failed GUI test.
    session_dir.rmdir()


def test_default_session_directory_is_cleaned_up():
    app = MotifApp(["/bin/true"])
    session_dir = Path(app.session_dir)

    assert session_dir.exists()

    app.__exit__(None, None, None)

    assert not session_dir.exists()


def test_start_requires_display(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/xdotool")
    app = MotifApp(["/bin/true"])

    with pytest.raises(MissingDisplay, match="DISPLAY"):
        app.start()

    app.__exit__(None, None, None)


def test_xdotool_failure_includes_command_output_and_captures_diagnostics(monkeypatch):
    app = MotifApp(["/bin/true"])
    labels = []

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="out", stderr="err")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(app, "capture_diagnostics", lambda label: labels.append(label))

    with pytest.raises(XdotoolError) as exc:
        app.press("Return")

    message = str(exc.value)
    assert "xdotool" in message
    assert "returncode=1" in message
    assert "stdout='out'" in message
    assert "stderr='err'" in message
    assert labels == ["xdotool_failed"]

    app.__exit__(None, None, None)


def test_input_methods_capture_diagnostics_on_xdotool_failure(monkeypatch):
    app = MotifApp(["/bin/true"])
    state = {
        "type": "snapshot",
        "t": 1.0,
        "widgets": [
            {
                "path": "app.button",
                "root_x": 10,
                "root_y": 20,
                "width": 30,
                "height": 40,
                "managed": True,
                "sensitive": True,
                "realized": True,
            }
        ],
    }
    app.state_file.write_text(__import__("json").dumps(state), encoding="utf-8")
    labels = []

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(app, "capture_diagnostics", lambda label: labels.append(label))

    calls = [
        lambda: app.click("app.button"),
        lambda: app.click_relative("app.button", 1, 2),
        lambda: app.click_root(1, 2),
        lambda: app.press("Return"),
        lambda: app.type_text("abc"),
    ]

    for call in calls:
        with pytest.raises(XdotoolError):
            call()

    assert labels == ["xdotool_failed"] * len(calls)

    app.__exit__(None, None, None)


def test_wait_until_returns_truthy_value():
    app = MotifApp(["/bin/true"], timeout=0.1)
    result = app.wait_until("value", lambda: "ready")

    assert result == "ready"

    app.__exit__(None, None, None)


def test_wait_until_times_out_and_captures_diagnostics(monkeypatch):
    app = MotifApp(["/bin/true"])
    labels = []
    monkeypatch.setattr(app, "capture_diagnostics", lambda label: labels.append(label))

    with pytest.raises(TimeoutError, match="never ready"):
        app.wait_until("never ready", lambda: False, timeout=0)

    assert labels == ["wait_until_failed"]

    app.__exit__(None, None, None)
