"""
Speech adapter for the dashboard.

Wraps app.speech.ConversationService. Optionally accepts a real
IntentResult (from the ML adapter) and/or real information_text (from
the Guide adapter) to hand into ConversationInput, exactly like any
other caller composing Speech with ML/Guide -- Speech itself is never
modified and never imports app.ml/app.guide directly.
"""

from __future__ import annotations

from typing import Optional

from app.models.schemas import IntentResult
from app.speech import (
    ConversationContext,
    ConversationInput,
    ConversationResponse,
    ConversationService,
    Language,
)
from app.ui.dashboard_view_models import HealthState, SubsystemStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SpeechAdapter:
    """Dashboard-facing wrapper around the real Speech & Conversation service."""

    def __init__(self) -> None:
        self._service: Optional[ConversationService] = None
        self._init_error: Optional[str] = None
        try:
            self._service = ConversationService()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Speech unavailable: %s", exc)
            self._init_error = str(exc)

    def status(self) -> SubsystemStatus:
        if self._service is None:
            return SubsystemStatus(
                name="Speech",
                state=HealthState.UNAVAILABLE,
                detail=self._init_error or "Speech service failed to initialize",
            )
        return SubsystemStatus(name="Speech", state=HealthState.PASS, detail="Conversation service ready")

    def handle(
        self,
        text: str,
        *,
        context: Optional[ConversationContext] = None,
        language: Optional[Language] = None,
        intent_result: Optional[IntentResult] = None,
        information_text: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> Optional[ConversationResponse]:
        if self._service is None:
            return None
        return self._service.handle(
            ConversationInput(
                text=text,
                language=language,
                intent=intent_result.intent if intent_result is not None else None,
                context=context,
                information_text=information_text,
                destination=destination,
            )
        )
