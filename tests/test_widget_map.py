from motiftap.widget_map import Snapshot, Widget, WidgetTimeline


def test_hit_test_prefers_deepest_widget():
    timeline = WidgetTimeline(
        [
            Snapshot(
                t=10.0,
                widgets=[
                    Widget("app", "app", "Shell", 0, 0, 500, 500, 0),
                    Widget("app.form", "form", "XmForm", 0, 0, 500, 500, 1),
                    Widget("app.form.ok", "ok", "XmPushButton", 100, 100, 50, 20, 2),
                ],
            )
        ]
    )

    widget = timeline.hit_test(10.5, 110, 110)
    assert widget is not None
    assert widget.path == "app.form.ok"


def test_hit_test_returns_none_when_no_match():
    timeline = WidgetTimeline(
        [Snapshot(t=1.0, widgets=[Widget("app", "app", "Shell", 0, 0, 10, 10, 0)])]
    )
    assert timeline.hit_test(1.0, 100, 100) is None
