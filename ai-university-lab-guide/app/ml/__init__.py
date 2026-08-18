"""
ML — Machine Learning module (SCAFFOLDED, NOT YET IMPLEMENTED).

Owner: Person 1 (AI / Intelligence).

Future responsibility: classify a student's free-text question into an
intent, so the future orchestration layer (app.main) can decide whether
to route the request toward Guide (information), Navigation (directions),
both (combined), a help response, or an unknown/fallback response.

Planned flow (not implemented in this phase):

    Student Question (str)
          |
          v
    Intent Classifier  (app.ml.service)
          |
          v
    IntentResult

Planned intents: INFORMATION, NAVIGATION, COMBINED, HELP, UNKNOWN.
Planned approach: TF-IDF + Logistic Regression (classic ML, not deep
learning — see app.dl for the future gesture-recognition DL module).

Dependency rules (enforced from the first real implementation onward):
    ML MUST NOT import app.robot
    ML MUST NOT import app.navigation
    ML MUST NOT import app.decision (implementation)
    ML communicates via shared contracts in app.models only

This package currently contains no logic — only the directory
structure (dataset/, training/, inference/, artifacts/) and this
docstring, prepared for future implementation in a dedicated ML phase.
"""
