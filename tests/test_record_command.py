from pathlib import Path

import pytest

from motiftap.commands import record
from motiftap.commands.record import (
    RecordingValidationError,
    _unexpected_exit,
    _validate_outputs,
)


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_validate_outputs_accepts_complete_cnee_recording(tmp_path):
    for name in ["meta.json", "latest-state.json", "widgets.jsonl", "xnee-human.txt"]:
        _write(tmp_path / name)

    _validate_outputs(
        meta_file=tmp_path / "meta.json",
        state_file=tmp_path / "latest-state.json",
        widget_log=tmp_path / "widgets.jsonl",
        xnee_human=tmp_path / "xnee-human.txt",
        used_cnee=True,
    )


def test_validate_outputs_reports_missing_hook_state(tmp_path):
    _write(tmp_path / "meta.json")
    _write(tmp_path / "widgets.jsonl")
    _write(tmp_path / "xnee-human.txt")

    with pytest.raises(RecordingValidationError, match="latest-state.json"):
        _validate_outputs(
            meta_file=tmp_path / "meta.json",
            state_file=tmp_path / "latest-state.json",
            widget_log=tmp_path / "widgets.jsonl",
            xnee_human=tmp_path / "xnee-human.txt",
            used_cnee=True,
        )


def test_validate_outputs_reports_empty_xnee_output(tmp_path):
    _write(tmp_path / "meta.json")
    _write(tmp_path / "latest-state.json")
    _write(tmp_path / "widgets.jsonl")
    _write(tmp_path / "xnee-human.txt", "")

    with pytest.raises(RecordingValidationError, match="xnee-human.txt"):
        _validate_outputs(
            meta_file=tmp_path / "meta.json",
            state_file=tmp_path / "latest-state.json",
            widget_log=tmp_path / "widgets.jsonl",
            xnee_human=tmp_path / "xnee-human.txt",
            used_cnee=True,
        )


def test_validate_outputs_skips_xnee_in_no_cnee_mode(tmp_path):
    _write(tmp_path / "meta.json")
    _write(tmp_path / "latest-state.json")
    _write(tmp_path / "widgets.jsonl")

    _validate_outputs(
        meta_file=tmp_path / "meta.json",
        state_file=tmp_path / "latest-state.json",
        widget_log=tmp_path / "widgets.jsonl",
        xnee_human=tmp_path / "xnee-human.txt",
        used_cnee=False,
    )


def test_unexpected_exit_reports_nonzero_subprocess_status():
    message = _unexpected_exit(name="application", argv=["./app", "--flag"], returncode=2)

    assert message is not None
    assert "application exited with status 2" in message
    assert "./app --flag" in message


def test_unexpected_exit_allows_expected_signal_cleanup():
    assert (
        _unexpected_exit(
            name="cnee",
            argv=["cnee", "--record"],
            returncode=-2,
            allow_signal=True,
        )
        is None
    )


class FakeProcess:
    def __init__(self, returncode: int | None = None, on_terminate=None, on_wait=None):
        self.returncode = returncode
        self._on_terminate = on_terminate
        self._on_wait = on_wait
        self.signals: list[int] = []
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self._on_wait:
            self._on_wait(self, timeout)
        return self.returncode

    def terminate(self):
        self.terminated = True
        if self._on_terminate:
            self._on_terminate(self)
        if self.returncode is None:
            self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def send_signal(self, sig):
        self.signals.append(sig)


def test_record_main_no_cnee_validates_hook_outputs(monkeypatch, tmp_path):
    def fake_popen(argv, env=None):
        def write_hook_outputs(proc):
            _write(Path(env["MOTIF_TAP_STATE"]))
            _write(Path(env["MOTIF_TAP_LOG"]))

        return FakeProcess(on_terminate=write_hook_outputs)

    monkeypatch.setattr(record.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(record.time, "sleep", lambda seconds: None)

    result = record.main(
        [
            "--name",
            "smoke",
            "--output-dir",
            str(tmp_path),
            "--seconds",
            "0",
            "--no-cnee",
            "--app",
            "fake-app",
        ]
    )

    assert result == 0
    assert (tmp_path / "smoke" / "meta.json").stat().st_size > 0
    assert not (tmp_path / "smoke" / "xnee-human.txt").exists()


def test_record_main_reports_positive_cnee_status_after_cleanup(monkeypatch, tmp_path):
    popen_calls = []

    def fake_popen(argv, env=None):
        popen_calls.append(argv)
        if argv[0] == "fake-app":
            return FakeProcess()

        def fail_after_cleanup(proc, timeout):
            proc.returncode = 2

        return FakeProcess(on_wait=fail_after_cleanup)

    monkeypatch.setattr(record.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(record.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr("builtins.input", lambda: "")

    with pytest.raises(SystemExit) as exc:
        record.main(
            [
                "--name",
                "smoke",
                "--output-dir",
                str(tmp_path),
                "--cnee",
                "cnee",
                "--app",
                "fake-app",
            ]
        )

    message = str(exc.value)
    assert "cnee exited with status 2" in message
    assert "xnee-human.txt" in message
