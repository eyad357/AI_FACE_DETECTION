"""
Decision state machine.

Consumes app.models.schemas.DetectionResult objects (produced upstream
by Vision, but this module never imports Vision — it only depends on the
shared contract) and produces application-level DecisionEvent objects
plus ApplicationState transitions.

Responsibility boundary:

    Vision   answers "What do I see?"          -> DetectionResult
    Decision answers "What should happen next?" -> DecisionEvent / state
    Robot    answers "How is it physically done?" (not here)

StateManager knows nothing about Robot SDKs, cameras, OpenCV, UI, or
Guide content. It is a plain, deterministic, in-process Python object.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.config import CONFIG
from app.decision.event_manager import (
    ApplicationState,
    DecisionEvent,
    DecisionEventType,
    GuideTopic,
    create_event,
)
from app.models.schemas import DetectionResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StateManager:
    """
    Deterministic finite state machine driving the guide interaction.

    Usage:
        manager = StateManager()
        events = manager.process(detection_result)   # each frame
        ...
        events = manager.complete_greeting()          # external signal
        events = manager.select_topic(GuideTopic.AI_PROJECTS)
        events = manager.complete_session()
        manager.reset()                                # recover from ERROR
    """

    def __init__(self) -> None:
        self._state: ApplicationState = ApplicationState.WAITING

        # Stability counters (frame-based, per Rule 9/10 of Phase 2 spec).
        self._consecutive_presence_frames: int = 0
        self._consecutive_absence_frames: int = 0

        # Edge-detection for presence-classification events, so we don't
        # emit NO_VISITOR/VISITOR_DETECTED/MULTIPLE_VISITORS every frame.
        self._last_presence_class: Optional[DecisionEventType] = None

        # Cooldown bookkeeping — timestamp-based (derived from the
        # DetectionResult timestamps fed into process()), not wall-clock,
        # so behavior stays deterministic given a fixed input sequence.
        self._cooldown_started_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Public read-only state
    # ------------------------------------------------------------------

    @property
    def state(self) -> ApplicationState:
        """Current application state."""
        return self._state

    # ------------------------------------------------------------------
    # Frame-driven processing
    # ------------------------------------------------------------------

    def process(self, detection_result: Optional[DetectionResult]) -> List[DecisionEvent]:
        """
        Process one Vision DetectionResult and return any DecisionEvents
        produced as a result.

        Args:
            detection_result: The latest detection result. Must be a
                valid DetectionResult instance.

        Returns:
            A list of DecisionEvents (possibly empty) produced by this
            call. Never raises for malformed input — invalid input is
            handled by transitioning to ApplicationState.ERROR and
            returning a single ERROR event.
        """
        if not self._is_valid_detection_result(detection_result):
            return self._enter_error(
                reason="process() received an invalid DetectionResult",
                timestamp=self._safe_timestamp(detection_result),
            )

        assert detection_result is not None  # narrowed by validation above
        events: List[DecisionEvent] = []

        events.extend(self._update_presence_classification(detection_result))

        if self._state is ApplicationState.WAITING:
            events.extend(self._process_waiting(detection_result))
        elif self._state is ApplicationState.COOLDOWN:
            events.extend(self._process_cooldown(detection_result))
        else:
            # GREETING / GUIDE_MENU / EXPLAINING / ERROR: transitions in
            # these states are driven by explicit orchestration signals
            # (complete_greeting/select_topic/complete_session/reset),
            # not by raw per-frame presence. We still track presence
            # classification above (for logging/telemetry) but do not
            # act on it here.
            logger.debug(
                "process() received a frame while in state=%s; no "
                "frame-driven transition applies in this state",
                self._state.value,
            )

        return events

    # ------------------------------------------------------------------
    # Explicit orchestration signals
    # ------------------------------------------------------------------

    def complete_greeting(self, timestamp: Optional[datetime] = None) -> List[DecisionEvent]:
        """
        Signal that the greeting has been physically completed
        (e.g. by the future Robot/orchestration layer).

        Valid only while in GREETING. Transitions GREETING -> GUIDE_MENU
        and emits GUIDE_MENU_REQUIRED. Invalid calls are rejected safely
        (logged, no state change, empty event list).
        """
        ts = timestamp or datetime.now()
        if self._state is not ApplicationState.GREETING:
            logger.warning(
                "complete_greeting() called while state=%s (expected "
                "GREETING); ignoring",
                self._state.value,
            )
            return []

        self._transition(ApplicationState.GUIDE_MENU)
        logger.info("GREETING -> GUIDE_MENU")
        return [create_event(DecisionEventType.GUIDE_MENU_REQUIRED, ts)]

    def select_topic(
        self, topic: GuideTopic, timestamp: Optional[datetime] = None
    ) -> List[DecisionEvent]:
        """
        Signal that a visitor selected a guide topic.

        Valid only while in GUIDE_MENU, and only for a genuine GuideTopic
        member. Transitions GUIDE_MENU -> EXPLAINING and emits
        TOPIC_SELECTED followed by EXPLANATION_REQUIRED. Invalid calls
        (wrong state or invalid topic) are rejected safely.
        """
        ts = timestamp or datetime.now()

        if self._state is not ApplicationState.GUIDE_MENU:
            logger.warning(
                "select_topic() called while state=%s (expected "
                "GUIDE_MENU); ignoring",
                self._state.value,
            )
            return []

        if not isinstance(topic, GuideTopic):
            logger.warning(
                "select_topic() called with invalid topic=%r; ignoring",
                topic,
            )
            return []

        self._transition(ApplicationState.EXPLAINING)
        logger.info("GUIDE_MENU -> EXPLAINING (topic=%s)", topic.value)

        return [
            create_event(
                DecisionEventType.TOPIC_SELECTED, ts, {"topic": topic.value}
            ),
            create_event(
                DecisionEventType.EXPLANATION_REQUIRED, ts, {"topic": topic.value}
            ),
        ]

    def complete_session(self, timestamp: Optional[datetime] = None) -> List[DecisionEvent]:
        """
        Signal that the explanation/session has finished.

        Valid only while in EXPLAINING. Transitions EXPLAINING ->
        COOLDOWN and emits SESSION_COMPLETED followed by
        COOLDOWN_STARTED. Invalid calls are rejected safely.
        """
        ts = timestamp or datetime.now()

        if self._state is not ApplicationState.EXPLAINING:
            logger.warning(
                "complete_session() called while state=%s (expected "
                "EXPLAINING); ignoring",
                self._state.value,
            )
            return []

        self._transition(ApplicationState.COOLDOWN)
        self._cooldown_started_at = ts
        self._consecutive_absence_frames = 0
        logger.info("EXPLAINING -> COOLDOWN")

        return [
            create_event(DecisionEventType.SESSION_COMPLETED, ts),
            create_event(DecisionEventType.COOLDOWN_STARTED, ts),
        ]

    def reset(self) -> None:
        """
        Force the state machine back to WAITING and clear all session
        state. Intended for recovering from ApplicationState.ERROR, or
        for orchestration-level resets (e.g. between demo runs).
        """
        logger.info("StateManager reset: %s -> WAITING", self._state.value)
        self._state = ApplicationState.WAITING
        self._consecutive_presence_frames = 0
        self._consecutive_absence_frames = 0
        self._last_presence_class = None
        self._cooldown_started_at = None

    # ------------------------------------------------------------------
    # Internal: per-state frame processing
    # ------------------------------------------------------------------

    def _process_waiting(self, detection_result: DetectionResult) -> List[DecisionEvent]:
        events: List[DecisionEvent] = []

        if detection_result.face_count >= 1:
            self._consecutive_presence_frames += 1
            self._consecutive_absence_frames = 0
        else:
            self._consecutive_presence_frames = 0

        logger.debug(
            "Detection stability = %d/%d",
            self._consecutive_presence_frames,
            CONFIG.vision.detection_frames_required,
        )

        if self._consecutive_presence_frames >= CONFIG.vision.detection_frames_required:
            self._transition(ApplicationState.GREETING)
            logger.info("WAITING -> GREETING")
            events.append(
                create_event(
                    DecisionEventType.GREETING_REQUIRED,
                    detection_result.timestamp,
                    {"face_count": detection_result.face_count},
                )
            )
            self._consecutive_presence_frames = 0

        return events

    def _process_cooldown(self, detection_result: DetectionResult) -> List[DecisionEvent]:
        events: List[DecisionEvent] = []

        if detection_result.face_count == 0:
            self._consecutive_absence_frames += 1
        else:
            self._consecutive_absence_frames = 0

        elapsed_seconds = 0.0
        if self._cooldown_started_at is not None:
            elapsed_seconds = (
                detection_result.timestamp - self._cooldown_started_at
            ).total_seconds()

        logger.debug(
            "Cooldown check: elapsed=%.2fs/%.2fs, absence=%d/%d",
            elapsed_seconds,
            CONFIG.decision.greeting_cooldown_seconds,
            self._consecutive_absence_frames,
            CONFIG.decision.visitor_lost_frames_required,
        )

        cooldown_time_elapsed = elapsed_seconds >= CONFIG.decision.greeting_cooldown_seconds
        visitor_confirmed_gone = (
            self._consecutive_absence_frames >= CONFIG.decision.visitor_lost_frames_required
        )

        if cooldown_time_elapsed and visitor_confirmed_gone:
            self._transition(ApplicationState.WAITING)
            logger.info("COOLDOWN -> WAITING")
            self._consecutive_presence_frames = 0
            self._consecutive_absence_frames = 0
            self._cooldown_started_at = None
            events.append(
                create_event(DecisionEventType.RETURN_TO_WAITING, detection_result.timestamp)
            )

        return events

    def _update_presence_classification(
        self, detection_result: DetectionResult
    ) -> List[DecisionEvent]:
        """
        Emit an edge-triggered presence classification event
        (NO_VISITOR / VISITOR_DETECTED / MULTIPLE_VISITORS) whenever the
        raw per-frame face count category changes. This avoids emitting
        the same status every single frame while still surfacing genuine
        changes as application-level events.
        """
        if detection_result.face_count == 0:
            current_class = DecisionEventType.NO_VISITOR
        elif detection_result.face_count == 1:
            current_class = DecisionEventType.VISITOR_DETECTED
        else:
            current_class = DecisionEventType.MULTIPLE_VISITORS

        events: List[DecisionEvent] = []
        if current_class != self._last_presence_class:
            logger.info(
                "Presence classification changed: %s -> %s",
                self._last_presence_class.value if self._last_presence_class else "NONE",
                current_class.value,
            )
            events.append(
                create_event(
                    current_class,
                    detection_result.timestamp,
                    {"face_count": detection_result.face_count},
                )
            )
        self._last_presence_class = current_class
        return events

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    def _transition(self, new_state: ApplicationState) -> None:
        self._state = new_state

    def _enter_error(
        self, reason: str, timestamp: Optional[datetime]
    ) -> List[DecisionEvent]:
        logger.error("Decision error: %s", reason)
        self._transition(ApplicationState.ERROR)
        ts = timestamp or datetime.now()
        return [create_event(DecisionEventType.ERROR, ts, {"reason": reason})]

    @staticmethod
    def _is_valid_detection_result(detection_result: Optional[DetectionResult]) -> bool:
        return isinstance(detection_result, DetectionResult)

    @staticmethod
    def _safe_timestamp(detection_result: Optional[DetectionResult]) -> Optional[datetime]:
        if isinstance(detection_result, DetectionResult):
            return detection_result.timestamp
        return None
