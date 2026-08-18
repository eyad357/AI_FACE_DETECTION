"""
PLACEHOLDER — not implemented in this phase.

This module will expose the public ML API once implemented, e.g.:

    from app.ml.service import IntentClassifierService

    classifier = IntentClassifierService()
    result = classifier.classify(question_text)   # -> IntentResult

Planned responsibility: "Given a student's free-text question, what is
their intent?" — nothing more. It will NOT decide what to do about that
intent (that remains the future orchestration layer's job, mirroring
how app.decision owns state and app.guide owns content today).

Dependency rules for the future implementation:
    - MUST NOT import app.robot
    - MUST NOT import app.navigation
    - MUST NOT import app.decision implementation (state_manager)
    - MAY use app.models for any shared result contract
    - MAY use app.config for centralized configuration
    - MAY use app.utils.logger for logging

Not implemented in this phase — this file intentionally contains no
executable logic yet.
"""
