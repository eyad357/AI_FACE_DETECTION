"""
DL — Deep Learning gesture-recognition subsystem.

Owner: Person 1 (AI / Intelligence).

Responsibility: recognize physical gestures from camera frames (a
deep-learning task, distinct from app.ml's classic-ML text intent
classification, and distinct from app.vision's face detection).

    from app.dl.service import GestureRecognitionService

    recognizer = GestureRecognitionService()
    result = recognizer.predict(frame)   # -> GestureResult

Flow:

    Input Frame (caller-provided NumPy array)
          |
          v
    app.dl.inference.preprocessing  (deterministic feature extraction)
          |
          v
    app.dl.models.network.GestureMLP  (small CPU-only NumPy MLP)
          |
          v
    app.dl.inference.engine.InferenceEngine  (confidence-threshold policy)
          |
          v
    GestureResult  (app.dl.models.gesture_types)

Gestures: WAVE, STOP, POINT, UNKNOWN (see
`app.dl.models.gesture_types.GestureLabel`) — exactly the vocabulary
already planned in `docs/architecture.md` prior to this implementation.

IMPORTANT — this module does NOT modify or replace app.vision. Face
detection remains app.vision's responsibility; gesture recognition is
a separate, additive capability that consumes its own caller-provided
frames through its own pipeline (dependency inversion: DL does not
own a camera or a frame source).

DL is a PRODUCER of semantic gesture information ONLY. It does not
decide what the robot should do and never talks to
`app.robot.RobotController` directly — a future integration/adapter
layer owns translating `GestureResult` into `app.robot` gesture
execution (see docs/dl.md "Integration boundary").

Dependency rules (enforced by tests/dl/test_dependency_isolation.py):
    DL MUST NOT import app.robot
    DL MUST NOT import app.vision
    DL MUST NOT import app.ml
    DL MUST NOT import app.navigation
    DL MUST NOT import app.decision (implementation)
    DL MUST NOT import app.guide
    DL MUST NOT import app.main

See docs/dl.md for full architecture, model lifecycle, training,
confidence semantics, error handling, and the integration contract.
"""
