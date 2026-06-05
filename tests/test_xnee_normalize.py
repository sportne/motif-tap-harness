from motiftap.xnee_normalize import normalize_xnee_human_lines


def test_normalize_cnee_human_button_events_with_root_coordinates():
    events = normalize_xnee_human_lines(
        [
            "Event=ButtonPress Number=4 { { root=0 event=0 child=0 rootX=10 rootY=20 eventX=0 eventY=0 state=0 sameScreen=0 } }",
            "Event=ButtonRelease Number=5 { { root=0 event=0 child=0 rootX=10 rootY=20 eventX=0 eventY=0 state=256 sameScreen=0 } }",
        ]
    )

    assert [event.phase for event in events] == ["press", "release"]
    assert [event.button for event in events] == [1, 1]
    assert [(event.x, event.y) for event in events] == [(10, 20), (10, 20)]
    assert [event.t for event in events] == [0.0, 0.001]


def test_normalize_ignores_malformed_human_lines():
    events = normalize_xnee_human_lines(
        [
            "noise without an event",
            "ButtonPress without coordinates",
            "KeyPress key=Return time=1.5",
        ]
    )

    assert len(events) == 1
    assert events[0].kind == "key"
    assert events[0].key == "Return"
    assert events[0].t == 1.5


def test_normalize_local_cnee_keyname_variant():
    events = normalize_xnee_human_lines(
        [
            "time=2.0 Event=KeyPress keyname=0x0061 a",
            "time=2.1 Event=KeyRelease keyname=0x0061 a",
        ]
    )

    assert [event.phase for event in events] == ["press", "release"]
    assert [event.key for event in events] == ["a", "a"]


def test_normalize_numeric_key_names():
    events = normalize_xnee_human_lines(
        [
            "time=3.0 Event=KeyPress key=1",
            "time=3.1 release key 2",
        ]
    )

    assert [event.phase for event in events] == ["press", "release"]
    assert [event.key for event in events] == ["1", "2"]
