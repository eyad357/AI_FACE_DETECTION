"""
PLACEHOLDER — not implemented in this phase.

This module will expose the public DL API once implemented, e.g.:

    from app.dl.service import GestureRecognitionService

    recognizer = GestureRecognitionService()
    result = recognizer.recognize(frame)   # -> GestureResult

Planned responsibility: "What gesture is being performed in this
frame?" — nothing more. It will NOT decide what the robot should do in
response (that remains the future orchestration layer's job).

Dependency rules for the future implementation:
    - MUST NOT import app.robot
    - MUST NOT import app.decision implementation (state_manager)
    - MUST NOT import app.navigation
    - MUST NOT import app.guide
    - MAY use app.models for any shared result contract
    - MAY use app.config for centralized configuration
    - MAY use app.utils.logger for logging

Not implemented in this phase — this file intentionally contains no
executable logic yet.
"""
