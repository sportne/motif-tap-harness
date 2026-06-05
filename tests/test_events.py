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


def test_coalesce_common_printable_and_shifted_keys():
    actions = coalesce_events(
        [
            RawEvent(t=1.0, kind="key", phase="press", key="bracketleft"),
            RawEvent(t=1.1, kind="key", phase="press", key="A"),
            RawEvent(t=1.2, kind="key", phase="press", key="exclam"),
            RawEvent(t=1.3, kind="key", phase="press", key="question"),
        ]
    )

    assert len(actions) == 1
    assert actions[0].op == "type_text"
    assert actions[0].data["text"] == "[A!?"


def test_coalesce_modifier_shortcut_as_press_action():
    actions = coalesce_events(
        [
            RawEvent(t=1.0, kind="key", phase="press", key="Alt_L"),
            RawEvent(t=1.1, kind="key", phase="press", key="f"),
            RawEvent(t=1.2, kind="key", phase="release", key="Alt_L"),
            RawEvent(t=1.3, kind="key", phase="press", key="o"),
        ]
    )

    assert [action.op for action in actions] == ["press", "type_text"]
    assert actions[0].data["key"] == "Alt_L+f"
    assert actions[1].data["text"] == "o"


def test_coalesce_editing_keys_as_press_actions():
    actions = coalesce_events(
        [
            RawEvent(t=1.0, kind="key", phase="press", key="a"),
            RawEvent(t=1.1, kind="key", phase="press", key="BackSpace"),
            RawEvent(t=1.2, kind="key", phase="press", key="Tab"),
        ]
    )

    assert [action.op for action in actions] == ["type_text", "press", "press"]
    assert actions[0].data["text"] == "a"
    assert actions[1].data["key"] == "BackSpace"
    assert actions[2].data["key"] == "Tab"


def test_coalesce_drag_fallback_is_preserved():
    actions = coalesce_events(
        [
            RawEvent(t=1.0, kind="button", phase="press", button=1, x=10, y=20),
            RawEvent(t=1.1, kind="button", phase="release", button=1, x=40, y=70),
        ]
    )

    assert actions[0].op == "drag_or_raw_mouse"
    assert actions[0].data["x1"] == 10
    assert actions[0].data["x2"] == 40
