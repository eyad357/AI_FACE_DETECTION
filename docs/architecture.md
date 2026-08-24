# Architecture

This document explains the existing, verified Phase 7 baseline and how
the new scaffolded modules (Phase 8) extend it — without changing
anything about how the Phase 7 modules already work.

## Phase 7 baseline (existing, protected)

As of Phase 7, the following pipeline is fully implemented and tested
(172 passed, 2 skipped):

```
Camera → Vision → DetectionResult → Decision → DecisionEvent
    → main.py → (GuideService, for EXPLANATION_REQUIRED) → GuideResponse
    → main.py → RobotCommand → RobotController → RobotExecutionResult
```

| Module | Responsibility | Status |
|---|---|---|
| `app/vision` | "What do I see?" — camera + face detection → `DetectionResult` | Frozen |
| `app/decision` | "What should happen next?" — state machine → `DecisionEvent` | Frozen |
| `app/guide` | "What information should be given?" — topic → `GuideResponse` | Frozen |
| `app/robot` | "How is it physically done?" — `RobotCommand` → `RobotExecutionResult` | Frozen |
| `app/models` | Shared, framework-independent data contracts | Frozen |
| `app/config` | Centralized, typed configuration | Frozen |
| `app/main` | Orchestrates the above (the only module allowed to import all of them) | Frozen |

Nothing in this list was modified to prepare the new architecture below.

## New scalable architecture (Phase 8 — scaffolded, not yet implemented)

```
app/
│
├── models/              SHARED CONTRACTS           (existing, frozen)
├── vision/               EXISTING / FROZEN
├── ml/                    NEW — scaffolded
├── dl/                    NEW — scaffolded
├── decision/             EXISTING / preserved
├── guide/                 EXISTING / preserved (extension point for later)
├── navigation/            NEW — scaffolded
├── robot/                EXISTING / Person 2, frozen
├── ui/                    EXISTING placeholder, scope clarified
├── config.py             EXISTING / shared
└── main.py                INTEGRATION ONLY (unchanged this phase)
```

### app/ml — Machine Learning (scaffolded)

*"What is the student asking for?"*

Planned flow: `Student Question -> Intent Classifier -> IntentResult`,
with intents `INFORMATION`, `NAVIGATION`, `COMBINED`, `HELP`, `UNKNOWN`,
planned to be implemented with TF-IDF + Logistic Regression.

Structure created this phase: `dataset/`, `training/`, `inference/`,
`artifacts/`, `service.py` — all placeholders, no logic yet.

### app/dl — Deep Learning (scaffolded)

*"What gesture is the visitor making?"*

Planned flow: `Camera Frame -> DL Model -> GestureResult`, with
gestures `WAVE`, `STOP`, `POINT`, `UNKNOWN`. This is separate from, and
must never replace, `app.vision`'s face-detection responsibility.

Structure created this phase: `models/`, `inference/`, `service.py` —
all placeholders, no logic yet.

### app/navigation — Navigation (scaffolded)

*"How do I get from A to B?"*

Planned flow: `RouteRequest -> Pathfinding -> RouteResult`, over a
university map representation (locations + connections).

Structure created this phase: `map_data.py`, `pathfinder.py`,
`service.py` — all placeholders, no logic yet.

### app/ui — UI (existing placeholder, scope clarified)

*"How is information displayed?"*

Already existed since Phase 1 as a placeholder (`app/ui/guide_ui.py`).
This phase clarifies its planned future scope to include route
display, current intent display, destination, robot status, and guide
information — all via shared result/contract objects, never a direct
Robot SDK dependency. Still no logic.

### app/decision and app/guide — preserved, extension points noted

Both remain exactly as implemented in Phases 2–3/7. Future phases may
extend Decision to consume `IntentResult`/`GestureResult` and extend
Guide with navigation-aware content, but **no such extension was made
in this phase** — both modules are byte-for-byte unchanged.

## What this phase deliberately does NOT do

- Train, download, or wire in any ML/DL model.
- Implement pathfinding, dataset handling, or gesture recognition.
- Connect `ml`/`dl`/`navigation`/`ui` to `main.py`, `app.decision`, or
  `app.robot`.
- Modify `app/vision`, `app/robot`, `app/models`, `app/config`,
  `app/decision`, `app/guide`, or `app/main.py`.

Those are all deferred to dedicated future implementation phases, exactly
as Vision/Decision/Guide/Robot/Integration were each built in their own
phase rather than all at once.

See [`contracts.md`](contracts.md) for the communication philosophy and
ownership model, and the main [`README.md`](../README.md) for the
overall project status.
