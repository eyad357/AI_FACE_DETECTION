# AI University Lab Guide Robot

An intelligent university laboratory guide robot: it will perceive
visitors via camera, decide when/how to engage them, and use a
physical robot to greet and explain the lab, the AI/robotics program,
and the training offered.

## Current phase

**Phase 2 — Decision module.** (Phase 1 — Architecture + Vision — is complete and frozen.)

This phase delivers:

- A complete, independent, testable **Decision** state machine (`app/decision`).
- Application-level events (`DecisionEvent`) consumed from Vision's `DetectionResult`, with zero import of `app.vision`.
- New Decision-specific settings added to the existing `app/config.py`.
- 28 new Decision tests, on top of the existing Vision/model tests.

Phase 1's Vision implementation was **not modified** in this phase — see
[Decision Module](#decision-module) below for what's new, and
[Integration notes for Person 2](#integration-notes-for-person-2) for
what's still ahead.

Robot control, Guide content, UI, and full `main.py` orchestration are
still **intentionally not implemented** — see [Future roadmap](#future-roadmap).

## Architecture

```
Camera
   │
   ▼
Vision / Perception        (app/vision)         ← implemented (Phase 1, frozen)
   │  DetectionResult
   ▼
Decision                   (app/decision)       ← implemented (Phase 2)
   │  DecisionEvent
   ▼
Guide Service               (app/guide)         ← placeholder
   │
   ▼
UI / User Interaction       (app/ui)            ← placeholder
   │
   ▼
Robot Controller             (app/robot)        ← placeholder (Person 2)
   │
   ▼
Robot Speech + Gestures
```

```
ai-university-lab-guide/
├── app/
│   ├── main.py              # future orchestration entry point (placeholder)
│   ├── config.py            # centralized, typed configuration
│   ├── vision/               # IMPLEMENTED (Phase 1, frozen) — perception layer
│   │   ├── camera.py         # camera lifecycle abstraction
│   │   ├── detector_interface.py
│   │   └── face_detector.py  # Haar-cascade face detector
│   ├── decision/             # IMPLEMENTED (Phase 2) — state machine + events
│   │   ├── state_manager.py  # StateManager: DetectionResult → ApplicationState/DecisionEvent
│   │   └── event_manager.py  # ApplicationState, DecisionEventType, DecisionEvent, GuideTopic
│   ├── robot/                # placeholder — Person 2's Robot Controller
│   ├── guide/                # placeholder — future guide content/service
│   ├── ui/                   # placeholder — future UI
│   ├── models/
│   │   └── schemas.py        # canonical DetectionResult / FaceDetection / BoundingBox
│   └── utils/
│       └── logger.py         # centralized logging
├── scripts/
│   └── run_vision_demo.py    # standalone Vision demo (no Robot/UI dependency)
├── tests/
│   ├── test_vision.py
│   ├── test_camera.py
│   └── test_models.py
├── docs/
│   └── integration_contract.md
├── requirements.txt
├── README.md
├── .gitignore
└── LICENSE
```

## Module responsibilities

| Module | Responsibility | Status |
|---|---|---|
| `app/vision` | Observe camera frames, produce `DetectionResult` | **Implemented (Phase 1, frozen)** |
| `app/decision` | Turn Vision output into stable, application-level events | **Implemented (Phase 2)** |
| `app/guide` | Decide/store guide content based on Decision events | Placeholder |
| `app/ui` | Present guide content / status to a screen | Placeholder |
| `app/robot` | Drive robot speech/gestures (Person 2) | Placeholder |
| `app/models` | Shared, framework-independent data contracts | **Implemented** |
| `app/config` | Centralized configuration | **Implemented** |
| `app/utils/logger` | Centralized logging | **Implemented** |

## Integration rules

1. **Vision must never import Robot.** Zero dependency `Vision → Robot`.
2. **Robot must never import Vision.** Zero dependency `Robot → Vision`.
3. **Shared data uses models.** All cross-module contracts live in `app/models/schemas.py` — no duplicated `DetectionResult`.
4. **Configuration is centralized** in `app/config.py`.
5. **Robot commands are a future contract** — documented in `app/robot/robot_commands.py`, not implemented or called.
6. **Public interfaces are stable** — `DetectionResult`, `FaceDetector.detect()`, `Camera.open()/read()/release()` should not change silently.
7. **Every module is independently testable** — Vision runs with no Robot, UI, Decision, Guide, database, or internet dependency.
8. **`app/main.py` is the future integration point** — not implemented yet.

See [`docs/integration_contract.md`](docs/integration_contract.md) for full details.

## Vision responsibilities

`app/vision` observes camera frames and reports standardized detection
results. It does **not** decide whether to greet a visitor, start a
session, choose a guide topic, or trigger any robot action — those are
future Decision-layer responsibilities.

Public API:

```python
from app.vision.camera import Camera
from app.vision.face_detector import FaceDetector

camera = Camera()
if camera.open():
    ok, frame = camera.read()
    if ok:
        detector = FaceDetector()
        result = detector.detect(frame)
        print(result.detected, result.face_count)
camera.release()
```

## Decision Module

Vision, Decision, and Robot each answer a different question:

- **Vision**: "What do I see?" → produces a `DetectionResult`.
- **Decision**: "What should the application do next?" → produces an
  `ApplicationState` + `DecisionEvent`s.
- **Robot**: "How does the robot physically act?" → not implemented yet
  (Person 2's responsibility); Decision never calls it directly.

`app/decision` consumes `DetectionResult` objects (via
`StateManager.process()`) and produces typed, application-level
events — it never imports `app.vision` or `app.robot`, and it contains
no guide text and no robot commands.

### State machine

```
WAITING → GREETING → GUIDE_MENU → EXPLAINING → COOLDOWN → WAITING
                                                     ↑         │
                                                     └─────────┘
```

- **WAITING** — no active interaction. Default/initial state.
- **GREETING** — a visitor was stably detected; `GREETING_REQUIRED` was emitted.
- **GUIDE_MENU** — greeting finished (`complete_greeting()`); `GUIDE_MENU_REQUIRED` was emitted.
- **EXPLAINING** — a topic was selected (`select_topic()`); `EXPLANATION_REQUIRED` was emitted.
- **COOLDOWN** — session completed (`complete_session()`); prevents re-greeting the same visitor.
- **ERROR** — invalid input was received; recover with `manager.reset()`.

### Detection stability

A single detected frame does not trigger a greeting. `WAITING → GREETING`
only fires once `CONFIG.vision.detection_frames_required` **consecutive**
frames report a visitor — a single missed frame resets the streak, so
flickery camera detections can't cause premature transitions.

### Visitor-lost stability & cooldown

Returning from `COOLDOWN` to `WAITING` requires **both**:

- `CONFIG.decision.visitor_lost_frames_required` consecutive frames with no visitor, **and**
- `CONFIG.decision.greeting_cooldown_seconds` of elapsed time (measured from `DetectionResult.timestamp`, not wall-clock, so behavior stays deterministic for a given input sequence).

This means a lingering visitor after their session ends won't
immediately retrigger `GREETING_REQUIRED`.

### Multiple visitor handling

Decision distinguishes `NO_VISITOR` / `VISITOR_DETECTED` /
`MULTIPLE_VISITORS` from `DetectionResult.face_count`, but performs
**no face recognition and no identity tracking** — only presence and
count.

### DecisionEvent

```python
DecisionEvent(
    event_type: DecisionEventType,  # e.g. GREETING_REQUIRED
    timestamp: datetime,
    metadata: dict,                 # e.g. {"face_count": 1}
)
```

### Integration boundary

Decision produces intents (`GREETING_REQUIRED`, `EXPLANATION_REQUIRED`,
etc.) for a **future orchestration layer** (`app/main.py`) to map onto
Robot behavior. Robot integration is **not implemented** in this phase.

## DetectionResult contract

Defined in `app/models/schemas.py`:

```python
DetectionResult(
    detected: bool,
    face_count: int,
    confidence: Optional[float],   # None if the detector has no true ML confidence
    timestamp: datetime,
    faces: List[FaceDetection],
)

FaceDetection(
    bounding_box: BoundingBox,     # x, y, width, height in pixels
    confidence: Optional[float],
)
```

The current `FaceDetector` implementation (OpenCV Haar cascade) does
**not** produce a true statistical confidence score, so `confidence` is
always `None`. This is intentional — no fake confidence values are
invented.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running tests

```bash
pytest tests/ -v
```

Camera and detection tests are designed to run without physical camera
hardware. Two Vision tests that require real face photographs are
skipped automatically unless fixture images are added — see
[`tests/fixtures/README.md`](tests/fixtures/README.md). All Decision
tests (`tests/test_decision.py`) use only synthetic `DetectionResult`
objects and require no camera, Robot, UI, or database.

## Running the Vision demo

```bash
python scripts/run_vision_demo.py
```

Opens your default camera, overlays bounding boxes and detection status
in a window, and exits on `q`. This demo does not call Robot, Decision,
Guide, or UI code — it exists purely to prove the Vision module works
standalone.

## Dependencies

- `opencv-python` — camera access and face detection
- `numpy` — array/image handling
- `pytest` — testing

No web framework, database, or cloud service is used in this phase.

## Error handling

- **Camera unavailable** → `Camera.open()` returns `False` and logs a warning; it never raises for a simply-missing device.
- **Invalid frame** → `FaceDetector.detect()` raises `ValueError` with a clear message.
- **No face** → valid `DetectionResult(detected=False, face_count=0)`.
- **Multiple faces** → valid `DetectionResult` with `face_count > 1`.

## Future roadmap

- **Phase 2:** Face recognition, multiple-visitor handling, Arabic/English support, voice commands.
- **Phase 3:** Visit/session logging, topic analytics, database, visitor statistics.
- **Phase 4:** Advanced perception, object detection, visitor tracking, smart recommendations.

## Integration notes for Person 2

- Implement `app/robot/robot_controller.py` and finalize `app/robot/robot_commands.py`. Your module must **never** `import app.vision` or `app.decision`.
- The Decision layer (`app/decision`, Phase 2) now exists and emits application-level `DecisionEvent`s (`GREETING_REQUIRED`, `EXPLANATION_REQUIRED`, `SESSION_COMPLETED`, etc.) — see [Decision Module](#decision-module). Your Robot Controller will eventually receive these (or events derived from them) from the future orchestration layer, **not** raw `DetectionResult` objects and **not** by importing Decision directly.
- The shared contracts you may depend on live in `app/models/schemas.py`; do not create your own duplicate types.
- Centralize any Robot-specific configuration (ports, SDK settings, timeouts) in `app/config.py` following the existing pattern.
- `app/main.py` will be extended later to wire Vision → Decision → Guide → UI → Robot together — you don't need to build that orchestration yourself.

This phase implements Vision and Decision independently. Robot
integration is intentionally not implemented.
