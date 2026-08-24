"""
DL adapter for the dashboard.

Wraps app.dl.service.GestureRecognitionService. Reports the real
model_source ("trained_artifact" vs "untrained_fixture") honestly --
the dashboard never claims a trained gesture model exists when it
does not. No live camera-driven gesture inference is triggered from
the dashboard (that requires a frame source the demo environment does
not have); the panel surfaces real model status/info instead.
"""

from __future__ import annotations

from typing import Optional

from app.ui.dashboard_view_models import HealthState, SubsystemStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DLAdapter:
    """Dashboard-facing wrapper around the real DL gesture-recognition service."""

    def __init__(self) -> None:
        self._service = None
        self._init_error: Optional[str] = None
        try:
            from app.dl.service import GestureRecognitionService

            self._service = GestureRecognitionService()
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("DL service unavailable: %s", exc)
            self._init_error = str(exc)

    def status(self) -> SubsystemStatus:
        if self._service is None:
            return SubsystemStatus(
                name="DL",
                state=HealthState.UNAVAILABLE,
                detail=self._init_error or "DL service failed to initialize",
            )
        if self._service.model_source == "trained_artifact":
            return SubsystemStatus(name="DL", state=HealthState.PASS, detail="Trained gesture model loaded")
        return SubsystemStatus(
            name="DL",
            state=HealthState.DEGRADED,
            detail=f"Running on {self._service.model_source} (no trained artifact) -- "
            "predictions are not meaningful gesture recognition",
        )

    def model_info(self) -> Optional[dict]:
        if self._service is None:
            return None
        return self._service.model_info
