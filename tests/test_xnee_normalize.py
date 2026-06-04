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
