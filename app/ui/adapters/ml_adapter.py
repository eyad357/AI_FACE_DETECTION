"""
ML adapter for the dashboard.

Wraps app.ml.service.MLIntentService. Never fabricates a confidence
score or intent -- the real trained artifact is used if present.
"""

from __future__ import annotations

from typing import Optional

from app.models.schemas import IntentResult
from app.ui.dashboard_view_models import HealthState, SubsystemStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MLAdapter:
    """Dashboard-facing wrapper around the real ML intent service."""

    def __init__(self) -> None:
        self._service = None
        self._init_error: Optional[str] = None
        try:
            from app.ml.service import MLIntentService

            self._service = MLIntentService()
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("ML service unavailable: %s", exc)
            self._init_error = str(exc)

    def status(self) -> SubsystemStatus:
        if self._service is None:
            return SubsystemStatus(
                name="ML",
                state=HealthState.UNAVAILABLE,
                detail=self._init_error or "ML service failed to initialize",
            )
        return SubsystemStatus(
            name="ML",
            state=HealthState.PASS,
            detail="Trained intent classifier loaded",
        )

    def predict(self, text: str) -> Optional[IntentResult]:
        """Real prediction from the trained artifact, or None if ML is unavailable."""
        if self._service is None:
            return None
        return self._service.predict(text)
