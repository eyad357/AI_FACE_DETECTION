# Contracts

This document explains how modules in this project are meant to
communicate, and who owns what, so that AI/Intelligence work (Person 1)
and Robotics/Interaction work (Person 2) can proceed in parallel without
breaking each other.

## Communication philosophy

Modules never call another module's internals directly. They exchange
**shared, typed contracts**:

```
Module A  →  Shared Contract  →  Module B
```

not:

```
Module A  →  Module B implementation
```

This is already how the existing (Phase 1–7) modules work, and it is
the same principle the new scaffolded modules (`ml`, `dl`,
`navigation`) must follow once implemented:

| Producer | Contract | Consumer |
|---|---|---|
| `app.vision` | `DetectionResult` (`app.models.schemas`) | `app.decision` |
| `app.decision` | `DecisionEvent` (`app.decision.event_manager`) | `app.main` |
| `app.guide` | `GuideResponse` (`app.guide.guide_service`) | `app.main` |
| `app.robot` | `RobotExecutionResult` (`app.robot.robot_controller`) | `app.main` |
| *(future)* `app.ml` | *(future)* `IntentResult` | `app.main` / `app.decision` |
| *(future)* `app.dl` | *(future)* `GestureResult` | `app.main` / `app.decision` |
| *(future)* `app.navigation` | *(future)* `RouteRequest` / `RouteResult` | `app.main` / `app.robot` |

`app.models` is the natural home for a contract once it genuinely needs
to be shared, but — following the precedent already set by
`DecisionEvent`, `GuideResponse`, and `RobotExecutionResult`, all of
which live in their producing module rather than `app.models` — a new
contract does not have to move to `app.models` just because it crosses
a module boundary. It only needs **one canonical definition**, wherever
that turns out to be, and every consumer must use that one definition
rather than inventing a duplicate.

## Non-negotiable dependency rules

```
Vision      MUST NOT import Robot
Robot       MUST NOT import Vision
ML          MUST NOT import Robot
DL          MUST NOT import Robot
ML          MUST NOT import Navigation
DL          MUST NOT import Navigation
ML          MUST NOT import Decision implementation
DL          MUST NOT import Decision implementation
Navigation  MUST NOT import the Robot SDK
Guide       MUST NOT import the Robot SDK
```

Modules communicate through shared contracts in `app/models/` (or a
producing module's own result type, per the table above). Configuration
belongs only in `app/config.py`. Robot commands are stable and are
never invented casually. `app/main.py` is the only orchestration layer.
No circular imports are permitted. Every module must eventually be
independently testable, with no physical hardware required.

## Ownership

**Person 1 — AI / Intelligence:**
- `app/ml/`
- `app/dl/`
- `app/navigation/`
- Decision extensions (future)
- AI evaluation

**Person 2 — Robotics / Interaction:**
- `app/robot/`
- Guide extensions (future)
- `app/ui/`
- Speech
- Gestures (robot-side behavior, as distinct from `app.dl`'s
  gesture *recognition*)
- Robot behavior
- UX evaluation

Ownership does **not** mean either person may break the other's
module. Any change to a shared contract requires agreement from both —
the same rule that has governed every phase of this project so far
(see `docs/integration_contract.md` for the full Phase 1–7 contract
history).

## Protected modules (as of this phase)

```
app/vision/     — frozen (Person 1's original Vision work)
app/robot/      — frozen (Person 2's Robot work)
app/models/     — frozen (shared contract layer)
app/config.py   — frozen (centralized configuration)
app/decision/   — preserved (behavior unchanged; future extension point)
app/guide/      — preserved (behavior unchanged; future extension point)
app/main.py     — unchanged this phase (future integration point for
                   ml/dl/navigation/ui, once those are implemented)
```

`app/ml/`, `app/dl/`, `app/navigation/`, and `app/ui/` are scaffolded
only — see [`architecture.md`](architecture.md) for what each is
planned to do, and the main [`README.md`](../README.md) for current
project status.
