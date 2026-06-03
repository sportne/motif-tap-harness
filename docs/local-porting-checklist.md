# Local porting checklist

Use this checklist when bringing Motif Tap Harness to a real application for the first time.

---

## 1. Confirm the application is a good candidate

Check:

```text
application runs under X11
application is dynamically linked
application uses Xt/Motif for most widgets
application can be launched with deterministic test data
application can run in a clean temporary HOME or profile
```

---

## 2. Build the hook

```bash
make -C c
```

If this fails, inspect:

```text
libXt development headers
X11 development headers
compiler availability
platform-specific Xt private header paths
```

---

## 3. Run the app with the hook only

```bash
mkdir -p /tmp/motif-tap
MOTIF_TAP_STATE=/tmp/motif-tap/latest-state.json \
MOTIF_TAP_LOG=/tmp/motif-tap/widgets.jsonl \
LD_PRELOAD=$PWD/c/libxttap.so \
/path/to/my_motif_app
```

Then:

```bash
motif-inspect-state /tmp/motif-tap/latest-state.json | head -50
```

You want to see meaningful widget paths and geometries.

---

## 4. Evaluate widget names

Good:

```text
myApp.mainWindow.form.applyButton
myApp.openDialog.fileText
myApp.completeDialog.okButton
```

Weak:

```text
myApp.form.button.button.button
myApp.dialog.form.child.child
```

If names are weak, the system can still work, but generated tests will be harder to maintain. Consider small GUI-builder/source changes to improve names.

---

## 5. Record one simple workflow

Pick something deterministic:

```text
launch app
open known file
wait for success dialog
close dialog
verify output file
```

Avoid drawing-heavy or drag-heavy workflows for the first pass.

---

## 6. Normalize Xnee output

```bash
motif-normalize-xnee recordings/name/xnee-human.txt \
  --out recordings/name/events.jsonl \
  --stats
```

If counts are zero or obviously wrong, adjust `src/motiftap/xnee_normalize.py` for your local cnee output.

---

## 7. Translate and inspect

```bash
motif-translate recordings/name --out tests/test_name.py
```

Review:

```text
HIGH count
LOW count
TODO count
```

Focus on LOW/TODO lines.

---

## 8. Add assertions

Add assertions that prove the application did the right thing.

Examples:

```python
assert Path(output_file).exists()
assert "completed successfully" in log_text
app.wait_for_widget("myApp.completeDialog.okButton")
```

---

## 9. Run in a controlled X11 session

Local:

```bash
pytest tests/test_name.py
```

Headless:

```bash
xvfb-run -a pytest tests/test_name.py
```

---

## 10. Iterate

After the first test works:

```text
add two or three more smoke workflows
factor common flows into helper methods
improve widget names where painful
archive useful recordings
set up CI artifacts
```
