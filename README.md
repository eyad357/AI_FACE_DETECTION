# AI University Lab Guide Robot

An intelligent university laboratory guide robot: it will perceive
visitors via camera, decide when/how to engage them, and use a
physical robot to greet and explain the lab, the AI/robotics program,
and the training offered.

## Current phase

**Phase 7 — Application integration / orchestration.** (Phases 1–6 — Vision, Decision, Guide, a shared-models audit, configuration hardening, and Robot — are complete and frozen.)

This phase delivers:

- `app/main.py` now contains a real orchestration layer — `ApplicationIntegration` — wiring Vision, Decision, Guide, and Robot together for the first time. This is the **only** module in the project allowed to import all four.
- The full pipeline works end-to-end: a `DetectionResult` (real or synthetic) drives Decision's state machine; resulting `DecisionEvent`s are mapped to `RobotCommand`s (`GREETING_REQUIRED`→`GREET`, `COOLDOWN_STARTED`/`RETURN_TO_WAITING`→`IDLE`, `ERROR`→`STOP`); `EXPLANATION_REQUIRED` additionally calls `GuideService.get_topic_content()` and maps the resulting `GuideResponse.spoken_text` to the matching `EXPLAIN_*` command.
- An optional `capture_and_handle()` wires in a real `Camera` + `FaceDetector` for a live-camera scenario; the core `handle_detection(detection_result)` API remains fully hardware-free (used by all tests).
- 25 new integration tests, on top of the existing Vision/Decision/Guide/Robot/config tests.
- **Zero** changes to Vision, Decision, Guide, Robot, shared models, or config — every mapping uses only contracts that already existed; nothing was renamed, redesigned, or invented.

See [Application Integration](#application-integration) below for the
full flow and the exact DecisionEvent → RobotCommand mapping table.

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
main.py — ApplicationIntegration                ← implemented (Phase 7)
   │  ├── Guide Service    (app/guide)           ← implemented (Phase 3, frozen)
   │  │      GuideResponse
   │  ▼
   ├── Robot Controller    (app/robot)           ← implemented (Phase 6, frozen)
   │
UI / User Interaction       (app/ui)            ← placeholder
   ▼
Robot Speech + Gestures
```

```
ai-university-lab-guide/
├── app/
│   ├── main.py              # IMPLEMENTED (Phase 7) — ApplicationIntegration orchestration layer
│   ├── config.py            # centralized, typed configuration
│   ├── vision/               # IMPLEMENTED (Phase 1, frozen) — perception layer
│   │   ├── camera.py         # camera lifecycle abstraction
│   │   ├── detector_interface.py
│   │   └── face_detector.py  # Haar-cascade face detector
│   ├── decision/             # IMPLEMENTED (Phase 2, frozen) — state machine + events
│   │   ├── state_manager.py  # StateManager: DetectionResult → ApplicationState/DecisionEvent
│   │   └── event_manager.py  # ApplicationState, DecisionEventType, DecisionEvent, GuideTopic
│   ├── robot/                # IMPLEMENTED (Phase 6) — action execution layer
│   │   ├── robot_commands.py # RobotCommandType, RobotCommand
│   │   └── robot_controller.py # RobotController, RobotBackend, SimulatedRobotBackend
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
| `app/guide` | Provide topic content based on a requested `GuideTopic` | **Implemented (Phase 3, frozen)** |
| `app/ui` | Present guide content / status to a screen | Placeholder |
| `app/robot` | Execute physical robot actions (Person 2) | **Implemented (Phase 6, frozen)** |
| `app/models` | Shared, framework-independent data contracts | **Implemented** |
| `app/config` | Centralized configuration | **Implemented** |
| `app/utils/logger` | Centralized logging | **Implemented** |
| `app/main` | Orchestrate Vision → Decision → Guide → Robot | **Implemented (Phase 7)** |

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

## Robot Module

Robot answers "how should the physical action be performed?" — it does
**not** decide *when* to act. It is the first module owned by Person 2
(Robotics), and this phase is its first real implementation (Phases
1–5 only carried documentation-only placeholders for it).

### Robot command vocabulary

The vocabulary documented back in Phase 1 is unchanged — no command was
renamed, removed, or added:

```python
class RobotCommandType(Enum):
    GREET, WAVE, SPEAK, EXPLAIN_AI, EXPLAIN_ROBOTICS, EXPLAIN_TRAINING, EXPLAIN_LAB, IDLE, STOP
```

```python
RobotCommand(
    command_type: RobotCommandType,
    text: Optional[str] = None,   # required (non-empty) for SPEAK/EXPLAIN_* commands
    metadata: Dict[str, Any] = {},
)
```

### Robot public API

```python
from app.robot import RobotController, RobotCommand, RobotCommandType

controller = RobotController()
controller.greet()
controller.wave()
controller.speak("Welcome to the lab.")
controller.execute(RobotCommand(RobotCommandType.EXPLAIN_AI, text=guide_response.spoken_text))
controller.stop()
```

Every call returns a `RobotExecutionResult(command_type, success, message)`
— errors (empty speech text, a backend failure) are reported as
`success=False` with a clear message rather than raising, so Robot
fails safely. `execute()` only raises `RobotError` for a genuine
programmer error (passing something that isn't a `RobotCommand`).

### Backend abstraction — no hardware required

No physical robot SDK exists in this project. `RobotController`
delegates to a pluggable `RobotBackend`; the default,
`SimulatedRobotBackend`, is deterministic and hardware-free — it
records and logs each command rather than pretending a physical action
occurred. Tests, CI, and this whole project run with zero robot
hardware, SDK, or network access. A real backend can be swapped in
later via `RobotController(backend=...)` without changing the public
API.

### Robot does NOT

- Import `app.vision`, `app.decision`, or `app.guide`.
- Inspect `DetectionResult`, `DecisionEvent`, `ApplicationState`, or `GuideResponse`.
- Decide *when* to greet, *what* topic to explain, or *what* to say — only *how* to deliver an already-decided command/text.
- Hold any educational content (that's Guide's job) or read any `app.config` value (none is currently needed).
- Orchestrate Vision, Decision, or Guide, or import `app.main`.

## Application Integration

`app/main.py` — specifically `ApplicationIntegration` — is the **only**
module allowed to import and coordinate Vision, Decision, Guide, and
Robot together. It answers "how are all modules orchestrated?" It does
not reimplement any of their behavior; it only calls each module's
existing public API.

### Public API

```python
from app.main import ApplicationIntegration
from app.decision.event_manager import GuideTopic

app = ApplicationIntegration()

# Hardware-free core (what tests use) — feed in a DetectionResult:
results = app.handle_detection(detection_result)

# Optional: wire in a real Camera + FaceDetector for a live-camera scenario:
app = ApplicationIntegration(camera=Camera(), detector=FaceDetector())
results = app.capture_and_handle()

# Explicit signals (mirrors StateManager's own API):
app.complete_greeting()
app.select_topic(GuideTopic.AI_PROJECTS)
app.complete_session()
app.reset()   # recover from ApplicationState.ERROR
```

Every call returns `List[RobotExecutionResult]` — whatever Robot
commands were dispatched as a result of that step (often empty, since
most Decision events require no Robot action).

### DecisionEvent → RobotCommand mapping

Only existing `RobotCommandType` values are used — nothing was
invented for this phase:

| DecisionEvent | RobotCommand |
|---|---|
| `GREETING_REQUIRED` | `GREET` |
| `COOLDOWN_STARTED` | `IDLE` |
| `RETURN_TO_WAITING` | `IDLE` |
| `ERROR` | `STOP` |
| `EXPLANATION_REQUIRED` | `GuideService.get_topic_content(topic)` → `EXPLAIN_AI` / `EXPLAIN_ROBOTICS` / `EXPLAIN_TRAINING` / `EXPLAIN_LAB` (with `text=spoken_text`) |
| `NO_VISITOR`, `VISITOR_DETECTED`, `MULTIPLE_VISITORS`, `GUIDE_MENU_REQUIRED`, `TOPIC_SELECTED`, `SESSION_COMPLETED` | *(none — informational, or a UI concern)* |

### Failure handling

A Robot execution failure (`RobotExecutionResult.success=False`) never
corrupts Decision state — Decision has already produced and returned
its event by the time Robot is dispatched. Any unexpected exception
while dispatching a single event is logged and skipped rather than
crashing the whole batch.

### What main.py does NOT do

- Reimplement Vision's camera/detection logic, Decision's state machine, Guide's content, or Robot's execution/backend logic.
- Hold Guide content strings.
- Introduce new `RobotCommandType` or `DecisionEventType` values, or new shared models.

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

## Configuration Module

`app/config.py` answers "what settings should the modules use?" — it is
infrastructure, not orchestration: it never starts Vision, never
instantiates Decision/Guide, and never runs the application (that
remains `app/main.py`'s job).

### Single source of truth

All configuration lives in `app/config.py` as typed, frozen dataclasses
grouped by consumer (`CameraConfig`, `VisionConfig`, `LoggingConfig`,
`DecisionConfig`), composed into one `AppConfig`, exposed as the single
shared `CONFIG` instance:

```python
from app.config import CONFIG

CONFIG.camera.index               # int
CONFIG.vision.haar_scale_factor   # float
CONFIG.decision.greeting_cooldown_seconds  # float
```

No per-module config files exist (`app/vision/config.py` etc.) and none
are needed — Robot and Guide currently read zero values from `CONFIG`,
so no `RobotConfig`/`GuideConfig` section has been added; one would be
added only once either module genuinely needs a setting.

### Environment overrides

Every value can be overridden via an environment variable (e.g.
`LABGUIDE_CAMERA_INDEX=1`, `LABGUIDE_GREETING_COOLDOWN_SECONDS=15`) —
useful for CI or a different machine without touching code. An unset or
empty variable falls back to the documented default.

### Validation

Every setting is validated when its dataclass is constructed (camera
index/width/height/fps, confidence thresholds, frame-count thresholds,
cooldown seconds, log level, etc.). Two distinct failure modes raise a
clear `ConfigurationError` naming the setting and the invalid value,
rather than silently falling back:

- An environment variable is **set but unparseable** (e.g. `LABGUIDE_CAMERA_INDEX=abc`).
- A value is **out of its valid range** (e.g. a negative camera index, or `haar_scale_factor <= 1.0`, which would otherwise fail inside OpenCV with a confusing error).

An unset/empty environment variable is not an error — it legitimately
uses the default.

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
(`tests/test_decision.py`), Guide tests (`tests/test_guide.py`),
configuration tests (`tests/test_config.py`), Robot tests
(`tests/test_robot.py`), and integration tests
(`tests/test_integration.py`) use only synthetic data and the
deterministic `SimulatedRobotBackend` — none require a camera, physical
robot, UI, or database.

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

## Future Architecture

**Planned / Scaffolded — not yet implemented.** Phase 8 prepared the
repository for a larger, more scalable architecture by adding empty
module scaffolding and documentation only. No new feature logic exists
yet — see [`docs/architecture.md`](docs/architecture.md) and
[`docs/contracts.md`](docs/contracts.md) for the full plan.

| New module | Responsibility (future) | Status |
|---|---|---|
| `app/ml` | Classify a student question into an intent (`INFORMATION`/`NAVIGATION`/`COMBINED`/`HELP`/`UNKNOWN`) via TF-IDF + Logistic Regression | **Scaffolded** — directory structure + docstrings only |
| `app/dl` | Recognize physical gestures (`WAVE`/`STOP`/`POINT`/`UNKNOWN`) from camera frames | **Scaffolded** — directory structure + docstrings only |
| `app/navigation` | University map representation + pathfinding (`RouteRequest` → `RouteResult`) | **Scaffolded** — file placeholders + docstrings only |
| `app/ui` | Display route, intent, destination, robot status, and guide information | Placeholder since Phase 1; scope clarified in Phase 8 |

None of these are wired into `app/main.py`, `app/decision`, or
`app/robot` yet, and `app/vision`/`app/robot`/`app/models`/`app/config`
were **not modified** to make room for them. Each will get its own
dedicated implementation phase, the same way Vision, Decision, Guide,
Robot, and Integration each did.

## Integration notes for Person 2

- `app/robot` is implemented (Phase 6) and now genuinely wired into the
  application by `app/main.py` (Phase 7) — `RobotController`,
  `RobotCommand`/`RobotCommandType`, and the `SimulatedRobotBackend`
  default are all in place, tested, and driven end-to-end from Decision
  and Guide output. See [Robot Module](#robot-module) and
  [Application Integration](#application-integration).
- If real hardware/SDK integration is needed later, implement a new
  `RobotBackend` subclass (see `app/robot/robot_controller.py`) and pass
  it to `RobotController(backend=...)`, which you can then pass into
  `ApplicationIntegration(robot_controller=...)` — neither
  `RobotController`'s nor `ApplicationIntegration`'s public API should
  need to change for that.
- Robot still never imports Decision, Guide, or `app.main` — the
  `DecisionEvent`/`GuideResponse` → `RobotCommand` mapping lives
  entirely in `app/main.py`, not in Robot.
- If Robot ever needs genuine configuration (e.g. a real backend's
  connection settings), add a `RobotConfig` section to `app/config.py`
  following the existing `CameraConfig`/`DecisionConfig` pattern — none
  was added in Phase 6 or 7 since nothing currently consumes one.

Vision, Decision, Guide, Robot, and the application integration layer
(`app/main.py`) are all now implemented. The `app/ui` layer remains the
only piece not yet built.
