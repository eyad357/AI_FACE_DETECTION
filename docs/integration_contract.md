# Integration Contract

This document defines the boundaries between modules so that Person 1
(Vision) and Person 2 (Robot) — and later, the Decision/Guide/UI layers
— can work independently and integrate without rewriting each other's
code.

## High-level pipeline

```
Camera → Vision → Decision → Guide Service → UI → Robot Controller → Robot Speech + Gestures
```

## Vision (this phase)

### Vision input

A single camera frame, as a BGR `numpy.ndarray` (as produced by
`app.vision.camera.Camera.read()`), or grayscale.

### Vision output

A `DetectionResult` from `app.models.schemas`. This is the **only**
contract Vision exposes to the rest of the application.

### Vision responsibility

Perception only: "is there a face in this frame, and where."

### Vision does **not** decide

- Whether to greet a visitor
- Whether a session should start
- Which guide topic to present
- Any robot action

Those decisions belong to the future **Decision** layer, which will
consume `DetectionResult` objects over time (e.g. using
`CONFIG.vision.detection_frames_required` for temporal stability) and
emit application-level events.

## Shared data contract

The canonical shared models live in `app/models/schemas.py`:

- `BoundingBox` — `x`, `y`, `width`, `height` (pixels, framework-independent)
- `FaceDetection` — `bounding_box`, `confidence` (`Optional[float]`)
- `DetectionResult` — `detected`, `face_count`, `confidence`,
  `timestamp`, `faces`

No other module may define its own copy of `DetectionResult` or
`FaceDetection`. `app/models/schemas.py` has zero dependencies on
Vision or Robot, so any module can safely import it without creating a
circular dependency.

## Dependency direction

```
Vision   → Models, Config, Logger
Decision → Models, Config, Logger
Guide    → Models, Config, Logger
Robot    → Models, Config, Logger
UI       → Models, Guide
Main     → all application modules (future orchestration)
```

Forbidden:

```
Vision → Robot        (never)
Robot  → Vision        (never)
Models → Vision/Robot  (never)
```

## Decision layer (implemented in Phase 2)

Consumes `DetectionResult` objects (from Vision, or any synthetic
source in tests — Decision never imports Vision) and produces
`ApplicationState` transitions plus `DecisionEvent` objects. Decision
answers "what should the application do next?" — it does not perform
greetings, does not speak, and does not control the robot.

### Decision input

`app.models.schemas.DetectionResult`, passed into
`StateManager.process(detection_result)`.

### Decision output

- `ApplicationState` (`app.decision.event_manager.ApplicationState`):
  `WAITING`, `GREETING`, `GUIDE_MENU`, `EXPLAINING`, `COOLDOWN`, `ERROR`.
  These are application states, not robot hardware states.
- `DecisionEvent` (`app.decision.event_manager.DecisionEvent`): a typed
  `event_type` (`DecisionEventType`) + `timestamp` + optional
  `metadata`. Event types: `NO_VISITOR`, `VISITOR_DETECTED`,
  `MULTIPLE_VISITORS`, `GREETING_REQUIRED`, `GUIDE_MENU_REQUIRED`,
  `TOPIC_SELECTED`, `EXPLANATION_REQUIRED`, `SESSION_COMPLETED`,
  `COOLDOWN_STARTED`, `RETURN_TO_WAITING`, `ERROR`.

### Decision public API

```python
from app.decision import StateManager, GuideTopic

manager = StateManager()
events = manager.process(detection_result)        # every frame
events = manager.complete_greeting()               # external signal
events = manager.select_topic(GuideTopic.AI_PROJECTS)
events = manager.complete_session()
manager.reset()                                     # recover from ERROR
```

### Decision does NOT

- Import `app.vision` (no camera, no OpenCV, no detector internals).
- Import `app.robot` (no Robot SDK, no Robot Controller, no Robot commands).
- Call any Robot method (`greet()`, `wave()`, `speak()`, `move()`, etc.).
- Contain guide/educational content (belongs to `app.guide.content`).
- Perform face recognition or track visitor identity — only presence
  and count.
- Orchestrate the full application (that remains `app.main`'s job).

### Decision configuration

Added to `app.config.DecisionConfig` (reusing the existing centralized
config pattern):

- `visitor_lost_frames_required` — consecutive no-detection frames
  before a visitor is considered gone during `COOLDOWN`.
- `greeting_cooldown_seconds` — minimum elapsed time (derived from
  `DetectionResult.timestamp`, not wall-clock) before `COOLDOWN` can
  return to `WAITING`.

Decision also reads the existing `CONFIG.vision.detection_frames_required`
(published by Vision in Phase 1 for exactly this purpose) to gate the
`WAITING -> GREETING` transition.

## Future Robot layer (owned by Person 2, not implemented in Phase 1 or Phase 2)

Will expose robot behavior (speech, gestures, movement) independently
of Vision's internals. This document does **not** dictate the internal
implementation of the Robot Controller — only the separation
principle: Robot receives application-level commands/events, never raw
Vision output, and never imports `app.vision`.

### Conceptual future robot commands (documentation only)

These are documented for planning purposes only. They are **not**
implemented, imported, or called anywhere in this phase:

```
GREET
WAVE
SPEAK
EXPLAIN_AI
EXPLAIN_ROBOTICS
EXPLAIN_TRAINING
EXPLAIN_LAB
IDLE
STOP
```

## Stability of this contract

Once published, `DetectionResult` / `FaceDetection` / `BoundingBox` and
the public `FaceDetector.detect()` / `Camera.open()/read()/release()`
APIs should be treated as stable (Phase 1). As of Phase 2, the Decision
public API — `StateManager.process()/complete_greeting()/select_topic()
/complete_session()/reset()`, `ApplicationState`, `DecisionEventType`,
`DecisionEvent`, and `GuideTopic` — is also treated as stable. If a
breaking change becomes necessary in a later phase, it must be
explicitly identified, documented here, and explained — not changed
silently.
