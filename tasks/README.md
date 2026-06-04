# Project Task Index

This directory tracks lightweight task specs for Motif Tap Harness. The first
set of tasks proved the harness against a real Motif application under X11. The
current task set focuses on moving the project beyond alpha quality while
keeping it minimal and simple.

The completed live-loop proof can:

1. Build the Xt tap hook.
2. Build and launch a small Motif calculator.
3. Record a scripted calculator workflow with `cnee`.
4. Normalize and translate the recording.
5. Replay the generated pytest through `MotifApp`.
6. Assert a real calculator result.

Task files are lightweight specs, not implementation notes after the fact. Keep
each task independently understandable and update its status as work progresses.

## Status Vocabulary

- `Proposed`: task is defined but not started.
- `In Progress`: someone is actively implementing the task.
- `Blocked`: work cannot continue without an explicit dependency or decision.
- `Done`: acceptance criteria and validation are complete.
- `Superseded`: replaced by another task or design.

## Task Types

- `AFK`: implementable without further human decisions.
- `HITL`: requires a human decision, review, or manual observation before it can
  be completed.

## Tasks

| Task | Type | Status | Depends on | Summary |
| --- | --- | --- | --- | --- |
| [0001](0001-container-live-loop-base.md) | AFK | Done | None | Add the container base for live-loop work. |
| [0002](0002-motif-calculator-app.md) | AFK | Done | 0001 | Add a real Motif calculator fixture app. |
| [0003](0003-hook-state-smoke-test.md) | AFK | Done | 0001, 0002 | Prove the Xt hook sees the calculator. |
| [0004](0004-automated-xnee-recording.md) | AFK | Done | 0003 | Script a deterministic `cnee` recording. |
| [0005](0005-translation-and-generated-test.md) | AFK | Done | 0004 | Translate the recording into a pytest. |
| [0006](0006-container-replay-test.md) | AFK | Done | 0005 | Replay the generated test in the container. |
| [0007](0007-demo-docs-and-ci-path.md) | AFK | Done | 0006 | Document the full demo and optional CI path. |
| [0008](0008-reproducible-quality-baseline.md) | AFK | Done | None | Make the fast quality baseline reproducible locally and in CI. |
| [0009](0009-recorder-output-validation.md) | AFK | Proposed | None | Validate recorder outputs and subprocess failures before reporting success. |
| [0010](0010-replay-diagnostics-and-waits.md) | AFK | Proposed | None | Improve replay diagnostics and add a small condition-wait helper. |
| [0011](0011-translation-review-report.md) | AFK | Proposed | None | Add translation reports and a TODO gate for generated tests. |
| [0012](0012-xt-hook-path-stability.md) | AFK | Proposed | None | Stabilize Xt hook widget paths and snapshot behavior. |
| [0013](0013-event-normalization-hardening.md) | AFK | Proposed | None | Expand practical event normalization coverage while preserving TODO fallbacks. |
| [0014](0014-automated-live-loop-gate.md) | AFK | Proposed | 0008 | Run the live-loop proof automatically for relevant changes. |

## Workflow

1. Pick the lowest-numbered `Proposed` task whose dependencies are `Done`.
2. Change its status to `In Progress` in the same change set as the
   implementation or in a small preparatory commit.
3. Stay inside the task's allowed paths unless the task is updated first.
4. Run every command listed in `Validation Required`.
5. Mark the task `Done` only after all acceptance criteria are met.

The live-loop proof is complete because task 0006 passes: the container records,
normalizes, translates, replays, and asserts a calculator result under Xvfb.
