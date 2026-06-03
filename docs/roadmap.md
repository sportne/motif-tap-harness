# Roadmap

This project is a starter. The roadmap below describes how to evolve it into a stronger internal testing tool.

---

## Milestone 1: prove the loop

Goal:

```text
record one workflow
normalize it
translate it
run generated pytest under X11
```

Tasks:

- Build `c/libxttap.so` on the target platform.
- Confirm `latest-state.json` contains meaningful widget paths.
- Adjust `xnee_normalize.py` for local cnee output.
- Generate one test.
- Add one real application assertion.

---

## Milestone 2: make translation reviewable

Tasks:

- Add an HTML or Markdown translation report.
- Include before/after screenshots.
- List every action with confidence.
- Highlight LOW/TODO actions.
- Show matched widget geometry and class.

---

## Milestone 3: harden the Xt hook

Tasks:

- Add sibling indexes for duplicate names.
- Add debounced snapshot writing.
- Intercept additional Xt initialization paths.
- Add environment flags for verbosity/filtering.
- Add platform-specific compile guards.
- Add optional linked-in hook mode.

---

## Milestone 4: improve generated test quality

Tasks:

- Prefer keyboard shortcuts for menu selections.
- Add widget alias support.
- Add reusable page-object/application helper generation.
- Add text-field detection and clearing helpers.
- Add better drag gesture generation.

---

## Milestone 5: application-specific power

Tasks:

- Add custom helpers for drawing areas.
- Expose domain model state through a test-only channel.
- Add log-reading helpers.
- Add output-file validators.
- Add snapshot comparison only where needed.

---

## Milestone 6: CI integration

Tasks:

- Run under Xvfb with a stable window manager.
- Capture artifacts on failure.
- Split smoke and long workflow suites.
- Add flaky-test quarantine strategy.
- Publish test reports.

---

## Guiding principle

Do not chase perfect GUI introspection before creating value.

A generated test with two review comments and a strong assertion is better than a perfect recorder that never ships.
