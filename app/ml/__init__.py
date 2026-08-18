"""
ML — Machine Learning module.

Owner: Person 1 (AI / Intelligence).

Responsibility: classify a student's free-text question into an intent,
so a future orchestration layer (app.main) can decide whether to route
the request toward Guide (information), Navigation (directions), both
(combined), a help response, or an unknown/fallback response.

Flow:

    Student Question (str)
          |
          v
    MLIntentService.predict()  (app.ml.service)
          |
          v
    IntentResult  (app.models.schemas)

Intents: INFORMATION, NAVIGATION, COMBINED, HELP, UNKNOWN.
Approach: TF-IDF + Logistic Regression (classic ML, not deep learning
-- see app.dl for the separate, unrelated gesture-recognition DL
module).

Dependency rules (enforced -- see docs/ml.md):
    ML MUST NOT import app.vision, app.robot, app.decision, app.guide,
    app.navigation, app.dl, app.ui, or app.main.
    ML communicates via shared contracts in app.models only.

This package contains:
    dataset/    labeled question -> intent training data + loader
    training/   offline training pipeline (never runs at runtime)
    inference/  runtime prediction from a trained artifact
    artifacts/  trained model artifact(s)
    service.py  public API (MLIntentService)

ML does NOT perform integration: it does not call Decision, Guide,
Navigation, Robot, Vision, DL, or UI, and it is not wired into
app.main in this phase. That remains a future integration phase.
"""
