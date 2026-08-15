# AI University Lab Guide Robot

An intelligent university laboratory guide robot: it will perceive
visitors via camera, decide when/how to engage them, and use a
physical robot to greet and explain the lab, the AI/robotics program,
and the training offered.

## Current phase

**Phase 1 — Architecture + Vision module.**

This phase delivers:

- The full modular project architecture (all future package folders exist).
- A complete, independent, testable **Vision** implementation.
- The shared data contract (`DetectionResult`) that every future module will use.
- Centralized configuration and logging.
- Unit tests and a standalone Vision demo.

Robot control, Decision logic, Guide content, UI, and full `main.py`
orchestration are **intentionally not implemented** in this phase —
see [Future roadmap](#future-roadmap) and
[Integration notes for Person 2](#integration-notes-for-person-2).

## Architecture

```
Camera
   │
   ▼
Vision / Perception        (app/vision)         ← implemented (Phase 1)
   │  DetectionResult
   ▼
Decision                   (app/decision)       ← placeholder
   │
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
│   ├── vision/               # IMPLEMENTED — perception layer
│   │   ├── camera.py         # camera lifecycle abstraction
│   │   ├── detector_interface.py
│   │   └── face_detector.py  # Haar-cascade face detector
│   ├── decision/             # placeholder — future state/event logic
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
| `app/vision` | Observe camera frames, produce `DetectionResult` | **Implemented** |
| `app/decision` | Turn Vision output into stable, application-level events | Placeholder |
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
[`tests/fixtures/README.md`](tests/fixtures/README.md).

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

- Implement `app/robot/robot_controller.py` and finalize `app/robot/robot_commands.py`. Your module must **never** `import app.vision`.
- You will eventually receive application-level events from the future Decision layer — not raw `DetectionResult` objects.
- The shared contracts you may depend on live in `app/models/schemas.py`; do not create your own duplicate types.
- Centralize any Robot-specific configuration (ports, SDK settings, timeouts) in `app/config.py` following the existing pattern.
- `app/main.py` will be extended later to wire Vision → Decision → Guide → UI → Robot together — you don't need to build that orchestration yourself.

This phase implements Vision independently. Robot integration is
intentionally not implemented.
