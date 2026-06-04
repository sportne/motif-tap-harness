from pathlib import Path

from motiftap.events import Action
from motiftap.translator import render_action, translate_recording
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
