"""
PLACEHOLDER — not implemented in Phase 1.

Future responsibility: consume app.models.schemas.DetectionResult
objects produced by the Vision layer and maintain application-level
state (e.g. whether a visitor is currently "stable" using
CONFIG.vision.detection_frames_required), independent of both Vision
and Robot.

Allowed future dependencies: app.models, app.config, app.utils.logger.
Must NOT import app.vision or app.robot directly for control coupling;
it depends only on the shared DetectionResult contract.
"""
