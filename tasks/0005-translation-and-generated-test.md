# Task: Translation And Generated Test

Status: Proposed
Type: AFK
Depends on: 0004

## Description

Translate the calculator recording into a pytest file and verify that the
recorded calculator interactions lift to widget-path actions. This task proves
the translator can consume a real `cnee` recording and real hook snapshots from
the containerized calculator.

## Allowed Changes

- `scripts/**` for translation automation.
- `tests/gui/**` for generated or curated GUI tests.
- `src/motiftap/translator.py` only for fixes required by real calculator
  translation defects.
- `src/motiftap/xnee_normalize.py` only for parser fixes identified in task
  0004.
- `tests/**` for focused translator or normalizer tests.

## Barred Changes

- Do not hand-edit generated output to hide translator defects before recording
  the defect.
- Do not relax confidence rules just to inflate `HIGH` counts.
- Do not commit large raw recordings.
- Do not add application-specific calculator helpers to `MotifApp`.

## Acceptance Criteria

- [ ] A script runs `motif-translate` against the calculator recording.
- [ ] The output pytest lives under `tests/gui/`.
- [ ] Most calculator button clicks translate to `app.click(widget_path)` with
      `HIGH` confidence.
- [ ] The generated pytest includes a result assertion or has a documented
      minimal post-generation patch that adds one.
- [ ] The translation command prints confidence counts.
- [ ] Any normalizer or translator code changes include unit tests.

## Validation Required

```bash
docker run --rm motif-tap-live-loop scripts/live-loop-translate.sh

make lint
make format-check
make test
```

The generated or curated test should contain widget-path clicks for calculator
buttons and an assertion for `/tmp/motif-calc/result.txt`.

## Notes

- The result assertion should check a stable string, for example `42`.
- If generated tests are committed, keep them readable and small.
- If generated tests are not committed, the script must write them to a known
  temp or artifact path and print that path.

