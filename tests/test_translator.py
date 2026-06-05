from pathlib import Path

import pytest

from motiftap.commands.translate import main as translate_main
from motiftap.events import Action
from motiftap.translator import render_action, render_report, translate_recording
from motiftap.widget_map import Snapshot, Widget, WidgetTimeline


def test_translate_example_recording():
    result = translate_recording(
        Path("examples/recordings/open_valid_file"),
        app_argv=["./examples/fake_motif_app", "--test-mode"],
        test_name="open_valid_file",
    )

    assert "def test_open_valid_file" in result.code
    assert "app.click('myApp.mainWindow.form.openButton'" in result.code
    assert "app.type_text('/tmp')" in result.code
    assert result.counts["HIGH"] >= 2
    assert result.rendered


def test_click_render_falls_back_to_latest_snapshot_when_early_snapshot_misses():
    timeline = WidgetTimeline(
        [
            Snapshot(t=10.0, widgets=[Widget("app", "app", "Shell", 0, 0, 1, 1, 0)]),
            Snapshot(
                t=12.0,
                widgets=[
                    Widget("app", "app", "Shell", 0, 0, 200, 200, 0),
                    Widget("app.button", "button", "XmPushButton", 10, 20, 30, 20, 1),
                ],
            ),
        ]
    )

    rendered = render_action(
        Action(t=10.0, op="click", data={"button": 1, "x": 15, "y": 25}),
        timeline,
    )

    assert rendered[0].confidence == "HIGH"
    assert "app.click('app.button'" in rendered[0].code
    assert "matched latest snapshot" in rendered[0].reason


def test_click_render_does_not_fallback_to_latest_snapshot_for_later_miss():
    timeline = WidgetTimeline(
        [
            Snapshot(t=10.0, widgets=[Widget("app", "app", "Shell", 0, 0, 1, 1, 0)]),
            Snapshot(
                t=12.0,
                widgets=[
                    Widget("app", "app", "Shell", 0, 0, 200, 200, 0),
                    Widget("app.button", "button", "XmPushButton", 10, 20, 30, 20, 1),
                ],
            ),
        ]
    )

    rendered = render_action(
        Action(t=11.0, op="click", data={"button": 1, "x": 15, "y": 25}),
        timeline,
    )

    assert rendered[0].confidence == "TODO"
    assert "app.click_root(15, 25" in rendered[0].code


def test_render_report_includes_counts_and_actions():
    result = translate_recording(
        Path("examples/recordings/open_valid_file"),
        app_argv=["./examples/fake_motif_app", "--test-mode"],
        test_name="open_valid_file",
    )

    report = render_report(result)

    assert "| HIGH |" in report
    assert "| TODO | 0 |" in report
    assert "myApp.mainWindow.form.openButton" in report
    assert "coalesced text input" in report


def test_translate_cli_writes_report_and_succeeds_without_todo(tmp_path):
    out = tmp_path / "test_open_valid_file.py"
    report = tmp_path / "report.md"

    result = translate_main(
        [
            "examples/recordings/open_valid_file",
            "--out",
            str(out),
            "--report",
            str(report),
            "--fail-on-todo",
            "--app",
            "./examples/fake_motif_app",
        ]
    )

    assert result == 0
    assert out.exists()
    assert report.exists()
    assert "Translation report: open_valid_file" in report.read_text(encoding="utf-8")


def test_translate_cli_fail_on_todo_still_writes_artifacts(tmp_path):
    recording = tmp_path / "todo_recording"
    recording.mkdir()
    (recording / "meta.json").write_text(
        '{"record_start_monotonic": 0, "app": ["./app"]}', encoding="utf-8"
    )
    (recording / "events.jsonl").write_text(
        '{"t": 1.0, "kind": "button", "phase": "press", "button": 1, "x": 500, "y": 500}\n'
        '{"t": 1.1, "kind": "button", "phase": "release", "button": 1, "x": 500, "y": 500}\n',
        encoding="utf-8",
    )
    (recording / "widgets.jsonl").write_text(
        '{"type":"snapshot","t":1.0,"widgets":[{"path":"app","class":"Shell","root_x":0,"root_y":0,"width":10,"height":10}]}\n',
        encoding="utf-8",
    )
    out = tmp_path / "test_todo.py"
    report = tmp_path / "report.md"

    with pytest.raises(SystemExit, match="TODO"):
        translate_main(
            [
                str(recording),
                "--out",
                str(out),
                "--report",
                str(report),
                "--fail-on-todo",
            ]
        )

    assert out.exists()
    assert report.exists()
    assert "| TODO | 1 |" in report.read_text(encoding="utf-8")
