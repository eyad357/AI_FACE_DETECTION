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

## Future Decision layer (not implemented in Phase 1)

Will consume `DetectionResult` objects from Vision, apply temporal
stability logic, and emit application-level events such as
`VISITOR_DETECTED`, `NO_VISITOR`, `GREETING_TRIGGER`, or
`SESSION_STARTED` toward the Guide/Robot layers.

## Future Robot layer (owned by Person 2, not implemented in Phase 1)

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
APIs should be treated as stable. If a breaking change becomes
necessary in a later phase, it must be explicitly identified,
documented here, and explained — not changed silently.
