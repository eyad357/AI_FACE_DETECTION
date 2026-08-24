"""
Training — offline training pipeline for the ML intent classifier.

Responsibility: fit a TF-IDF + Logistic Regression pipeline on the
labeled dataset (app.ml.dataset) and persist it to app.ml.artifacts.

See app.ml.training.train for the actual pipeline. This package
intentionally does not import that module at package-import time, so
that importing app.ml.training (and anything that transitively imports
app.ml) never pulls in scikit-learn unless training is explicitly
requested.

Training is offline-only: run explicitly via

    python -m app.ml.training.train

It must never run automatically as a side effect of application
startup or runtime inference (see app.ml.inference / app.ml.service).
"""
