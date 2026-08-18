"""
DL — Deep Learning module (SCAFFOLDED, NOT YET IMPLEMENTED).

Owner: Person 1 (AI / Intelligence).

Future responsibility: recognize physical gestures from camera frames
(a deep-learning task, distinct from app.ml's classic-ML text intent
classification, and distinct from app.vision's face detection).

Planned flow (not implemented in this phase):

    Camera Frame
          |
          v
    DL Model  (app.dl.inference, using app.dl.models)
          |
          v
    GestureResult

Planned gestures: WAVE, STOP, POINT, UNKNOWN.

IMPORTANT — this module must NOT modify or replace app.vision. Face
detection remains app.vision's responsibility; gesture recognition is a
separate, additive capability that will consume its own camera frames
through its own pipeline.

Dependency rules (enforced from the first real implementation onward):
    DL MUST NOT import app.robot
    DL MUST NOT import app.decision (implementation)
    DL MUST NOT import app.navigation
    DL MUST NOT import app.guide

This package currently contains no logic — only the directory
structure (models/, inference/) and this docstring, prepared for
future implementation in a dedicated DL phase.
"""
