"""
Inference — runtime intent prediction for the ML intent classifier.

Responsibility: load a trained artifact from app.ml.artifacts and run
inference (question -> intent) at request time. Consumed by
app.ml.service, which exposes the public IntentClassifierService API.

See app.ml.inference.inference for the implementation.
"""
