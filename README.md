# AI University Lab Guide Robot

An intelligent university laboratory guide robot: it will perceive
visitors via camera, decide when/how to engage them, and use a
physical robot to greet and explain the lab, the AI/robotics program,
and the training offered.

## Current phase

**Phase 3 — Guide module.** (Phases 1–2 — Vision and Decision — are complete and frozen.)

This phase delivers:

- A complete, independent, testable **Guide** content/service layer (`app/guide`).
- Structured topic content (`app/guide/content.py`) and a `GuideService.get_topic_content()` API returning a `GuideResponse`.
- Reuse of the existing `GuideTopic` contract (already defined in `app/decision/event_manager.py`) — no duplicate topic enum was created.
- 19 new Guide tests, on top of the existing Vision/Decision/model tests.

Phase 1's Vision and Phase 2's Decision were **not modified** in this
phase — see [Guide Module](#guide-module) below for what's new.

Robot control, UI, and full `main.py` orchestration are still
**intentionally not implemented** — see [Future roadmap](#future-roadmap).

## Architecture

```
Camera
   │
   ▼
Vision / Perception        (app/vision)         ← implemented (Phase 1, frozen)
   │  DetectionResult
   ▼
Decision                   (app/decision)       ← implemented (Phase 2, frozen)
   │  DecisionEvent
   ▼
Guide Service               (app/guide)         ← implemented (Phase 3)
   │  GuideResponse
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
│   ├── decision/             # IMPLEMENTED (Phase 2, frozen) — state machine + events
│   │   ├── state_manager.py  # StateManager: DetectionResult → ApplicationState/DecisionEvent
│   │   └── event_manager.py  # ApplicationState, DecisionEventType, DecisionEvent, GuideTopic
│   ├── robot/                # placeholder — Person 2's Robot Controller
│   ├── guide/                # IMPLEMENTED (Phase 3) — content + service layer
│   │   ├── guide_service.py  # GuideService.get_topic_content() → GuideResponse
│   │   └── content.py        # Static topic content, keyed by the existing GuideTopic enum
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
| `app/decision` | Turn Vision output into stable, application-level events | **Implemented (Phase 2, frozen)** |
| `app/guide` | Provide topic content based on a requested `GuideTopic` | **Implemented (Phase 3)** |
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

## Guide Module

Vision, Decision, Guide, and Robot each answer a different question:

- **Vision**: "What do I see?" → produces a `DetectionResult`.
- **Decision**: "What should the application do next?" → produces `DecisionEvent`s.
- **Guide**: "What information should be provided?" → produces a `GuideResponse`.
- **Robot**: "How does the robot physically act?" → not implemented yet (Person 2's responsibility).

`app/guide` is a content + service layer, not an orchestrator. It does
**not** decide whether a visitor exists, does not manage application
state, does not control the robot, does not perform speech synthesis,
and does not render UI.

### Guide input

A `GuideTopic` — reusing the **existing** enum already defined in
`app/decision/event_manager.py` (`AI_PROJECTS`, `ROBOTICS`, `TRAINING`,
`LAB_INFORMATION`). No second topic enum was created; Guide imports
this one symbol from Decision's event vocabulary and nothing else from
`app.decision` (never `app.decision.state_manager`, never Decision's
state machine behavior).

### Guide output — `GuideResponse`

```python
GuideResponse(
    topic: Optional[GuideTopic],
    title: str,
    summary: str,
    sections: List[str],
    spoken_text: str,   # plain text for a future orchestration layer to hand to Robot/UI
    timestamp: datetime,
)
```

No equivalent shared model existed anywhere in the project, so this is
a new, additive contract. It intentionally lives in `app/guide/guide_service.py`
rather than `app/models/schemas.py` — the same pattern already used by
`DecisionEvent`, which lives in `app.decision.event_manager` rather
than `app.models`. This also avoids introducing an
`app.models → app.decision` dependency, which would violate
`app/models/schemas.py`'s existing "no app-internal imports" contract.

### Guide public API

```python
from app.guide import GuideService
from app.decision.event_manager import GuideTopic

service = GuideService()
response = service.get_topic_content(GuideTopic.AI_PROJECTS)
```

Unknown/invalid topics return a controlled `GuideResponse` (`title="Topic Unavailable"`)
rather than raising — normal invalid input never crashes the service.

### Guide does NOT

- Import `app.vision` or `app.robot`.
- Import `app.decision.state_manager`, or inspect Decision states/transitions.
- Perform speech synthesis, render UI, or control the robot.
- Orchestrate the application (that remains `app.main`'s job).

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
[`tests/fixtures/README.md`](tests/fixtures/README.md). Decision tests
(`tests/test_decision.py`) and Guide tests (`tests/test_guide.py`) use
only synthetic data and require no camera, Robot, UI, or database.

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

- Implement `app/robot/robot_controller.py` and finalize `app/robot/robot_commands.py`. Your module must **never** `import app.vision`, `app.decision`, or `app.guide`.
- The Decision layer (`app/decision`, Phase 2) emits application-level `DecisionEvent`s (`GREETING_REQUIRED`, `EXPLANATION_REQUIRED`, `SESSION_COMPLETED`, etc.) — see [Decision Module](#decision-module).
- The Guide layer (`app/guide`, Phase 3) turns a selected `GuideTopic` into a `GuideResponse` with `spoken_text` your Robot Controller can eventually speak — see [Guide Module](#guide-module). You will receive this (or data derived from it) from the future orchestration layer, **not** by importing Guide directly.
- The shared contracts you may depend on live in `app/models/schemas.py`; do not create your own duplicate types.
- Centralize any Robot-specific configuration (ports, SDK settings, timeouts) in `app/config.py` following the existing pattern.
- `app/main.py` will be extended later to wire Vision → Decision → Guide → UI → Robot together — you don't need to build that orchestration yourself.

This phase implements Vision, Decision, and Guide independently. Robot
integration is intentionally not implemented.
