from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from motiftap.events import Action, coalesce_events, read_normalized_events
from motiftap.widget_map import Widget, WidgetTimeline

ACTIVATABLE_CLASS_HINTS = (
    "PushButton",
    "ToggleButton",
    "CascadeButton",
    "DrawnButton",
    "ArrowButton",
    "List",
    "Text",
    "Scale",
    "ScrollBar",
    "FileSelectionBox",
    "SelectionBox",
)


@dataclass(frozen=True)
class RenderedLine:
    code: str
    confidence: str
    reason: str
    action: str = ""
    target: str = ""


def safe_test_name(name: str) -> str:
    out = re.sub(r"[^0-9A-Za-z_]+", "_", name.strip()).strip("_").lower()
    if not out:
        out = "recorded_workflow"
    if out[0].isdigit():
        out = f"workflow_{out}"
    return out


def confidence_for(widget: Widget) -> str:
    if any(hint in widget.klass for hint in ACTIVATABLE_CLASS_HINTS):
        return "HIGH"
    if widget.depth >= 4:
        return "MEDIUM"
    return "LOW"


def _render_click(action: Action, timeline: WidgetTimeline) -> RenderedLine:
    x = int(action.data["x"])
    y = int(action.data["y"])
    button = int(action.data.get("button", 1))
    widget = timeline.hit_test(action.t, x, y)
    snapshot_reason = f"recorded at root ({x}, {y})"
    if widget is None and action.t <= timeline.snapshots[0].t:
        widget = timeline.hit_test(timeline.snapshots[-1].t, x, y)
        snapshot_reason = f"recorded at root ({x}, {y}); matched latest snapshot"

    if widget is None:
        return RenderedLine(
            code=f"        app.click_root({x}, {y}, button={button})",
            confidence="TODO",
            reason="no widget matched the recorded root coordinate",
            action="click",
            target=f"root ({x}, {y})",
        )

    confidence = confidence_for(widget)
    if confidence in {"HIGH", "MEDIUM"}:
        return RenderedLine(
            code=f"        app.click({widget.path!r}, button={button})",
            confidence=confidence,
            reason=f"{widget.klass}, {snapshot_reason}",
            action="click",
            target=widget.path,
        )

    rel_x = x - widget.root_x
    rel_y = y - widget.root_y
    return RenderedLine(
        code=f"        app.click_relative({widget.path!r}, {rel_x}, {rel_y}, button={button})",
        confidence="LOW",
        reason=f"parent-relative fallback inside {widget.klass}",
        action="click_relative",
        target=f"{widget.path} +{rel_x},{rel_y}",
    )


def render_action(action: Action, timeline: WidgetTimeline) -> list[RenderedLine]:
    if action.op == "click":
        return [_render_click(action, timeline)]

    if action.op == "press":
        key = str(action.data["key"])
        return [
            RenderedLine(
                code=f"        app.press({key!r})",
                confidence="HIGH",
                reason="keyboard action",
                action="press",
                target=key,
            )
        ]

    if action.op == "type_text":
        text = str(action.data["text"])
        return [
            RenderedLine(
                code=f"        app.type_text({text!r})",
                confidence="HIGH",
                reason="coalesced text input",
                action="type_text",
                target=text,
            )
        ]

    if action.op == "drag_or_raw_mouse":
        return [
            RenderedLine(
                code=f"        # TODO: drag gesture recorded; review manually: {action.data!r}",
                confidence="TODO",
                reason="drag gestures need application-specific handling",
                action="drag_or_raw_mouse",
                target=str(action.data),
            )
        ]

    return [
        RenderedLine(
            code=f"        # TODO: unhandled action {action.op!r}: {action.data!r}",
            confidence="TODO",
            reason="unknown action",
            action=action.op,
            target=str(action.data),
        )
    ]


@dataclass(frozen=True)
class TranslationResult:
    code: str
    counts: dict[str, int]
    rendered: list[RenderedLine]


def render_report(result: TranslationResult, *, title: str = "Translation report") -> str:
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        "| Confidence | Count |",
        "| --- | ---: |",
    ]
    for key in ["HIGH", "MEDIUM", "LOW", "TODO"]:
        lines.append(f"| {key} | {result.counts.get(key, 0)} |")

    lines.extend(
        [
            "",
            "## Actions",
            "",
            "| # | Confidence | Action | Target | Reason |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )

    for index, rendered in enumerate(result.rendered, start=1):
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                index,
                _report_cell(rendered.confidence),
                _report_cell(rendered.action or "unknown"),
                _report_cell(rendered.target),
                _report_cell(rendered.reason),
            )
        )

    return "\n".join(lines) + "\n"


def _report_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def generate_test(
    *,
    app_argv: list[str],
    normalized_events: str | Path,
    widget_log: str | Path,
    meta_file: str | Path,
    test_name: str,
) -> TranslationResult:
    meta = json.loads(Path(meta_file).read_text(encoding="utf-8"))
    session_start = float(meta.get("record_start_monotonic", 0.0))

    events = read_normalized_events(normalized_events, session_start_monotonic=session_start)
    actions = coalesce_events(events)
    timeline = WidgetTimeline.from_jsonl(widget_log)

    function_name = safe_test_name(test_name)
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "TODO": 0}
    rendered_actions: list[RenderedLine] = []

    lines: list[str] = [
        "from motiftap.harness import MotifApp",
        "",
        "",
        f"def test_{function_name}():",
        f"    with MotifApp({app_argv!r}) as app:",
        "        app.wait_for_idle()",
    ]

    for action in actions:
        rendered_lines = render_action(action, timeline)
        for rendered in rendered_lines:
            counts[rendered.confidence] = counts.get(rendered.confidence, 0) + 1
            rendered_actions.append(rendered)
            if rendered.code.strip().startswith("#"):
                lines.append(rendered.code)
            else:
                lines.append(f"{rendered.code}  # {rendered.confidence}: {rendered.reason}")

    lines.extend(
        [
            "",
            "        # Add real application assertions below.",
            "        # Prefer files, logs, database state, dialogs, or domain results over screenshots.",
            "        # Example:",
            "        # assert Path('/tmp/output.dat').exists()",
        ]
    )

    return TranslationResult(code="\n".join(lines) + "\n", counts=counts, rendered=rendered_actions)


def translate_recording(
    recording_dir: str | Path, *, app_argv: list[str] | None, test_name: str | None = None
) -> TranslationResult:
    directory = Path(recording_dir)
    meta_file = directory / "meta.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    if app_argv is None:
        app_argv = list(meta.get("app", []))
    if not app_argv:
        raise ValueError("No app argv supplied and recording meta.json did not contain one")

    return generate_test(
        app_argv=app_argv,
        normalized_events=directory / "events.jsonl",
        widget_log=directory / "widgets.jsonl",
        meta_file=meta_file,
        test_name=test_name or directory.name,
    )
