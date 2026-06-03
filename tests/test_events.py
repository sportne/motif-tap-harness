from motiftap.events import RawEvent, coalesce_events


def test_coalesce_click():
    actions = coalesce_events(
        [
            RawEvent(t=1.0, kind="button", phase="press", button=1, x=10, y=20),
            RawEvent(t=1.1, kind="button", phase="release", button=1, x=10, y=20),
        ]
    )

    assert len(actions) == 1
    assert actions[0].op == "click"
    assert actions[0].data["x"] == 10
    assert actions[0].data["y"] == 20


def test_coalesce_text():
    actions = coalesce_events(
        [
            RawEvent(t=1.0, kind="key", phase="press", key="slash"),
            RawEvent(t=1.1, kind="key", phase="press", key="t"),
            RawEvent(t=1.2, kind="key", phase="press", key="m"),
            RawEvent(t=1.3, kind="key", phase="press", key="p"),
            RawEvent(t=2.0, kind="key", phase="press", key="Return"),
        ]
    )

    assert actions[0].op == "type_text"
    assert actions[0].data["text"] == "/tmp"
    assert actions[1].op == "press"
    assert actions[1].data["key"] == "Return"
