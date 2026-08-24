"""
Application integration / orchestration.

This is the ONLY module allowed to connect Vision, Decision, Guide, and
Robot together. Each of those modules remains independently usable and
testable without this file — main.py only coordinates their EXISTING
public APIs; it does not reimplement any of their behavior, hold any
Guide content, or know about Robot backend/SDK details.

    Vision   "What do I see?"                    -> DetectionResult
    Decision "What should happen next?"           -> DecisionEvent
    Guide    "What information should be given?"  -> GuideResponse
    Robot    "How is it physically done?"         -> RobotExecutionResult
    main.py  "How are all of the above wired together?"

Flow:

    Camera -> Vision -> DetectionResult -> Decision -> DecisionEvent
        -> main.py -> (GuideService, only for EXPLANATION_REQUIRED)
        -> GuideResponse -> main.py -> RobotCommand -> RobotController

Run:

    python -c "from app.main import ApplicationIntegration; ApplicationIntegration()"

or see scripts/run_vision_demo.py for a standalone Vision-only demo.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.decision.event_manager import DecisionEvent, DecisionEventType, GuideTopic
from app.decision.state_manager import StateManager
from app.guide import GuideService
from app.models.schemas import DetectionResult
from app.robot import (
    RobotCommand,
    RobotCommandType,
    RobotController,
    RobotExecutionResult,
)
from app.utils.logger import get_logger
from app.vision.camera import Camera
from app.vision.detector_interface import FaceDetectorInterface

logger = get_logger(__name__)


# DecisionEventType -> RobotCommandType, for events that require no
# additional information beyond "perform this action". Only EXISTING
# RobotCommandType values are used here — none were invented for this
# phase (Rule 5 / Rule 8: Robot Commands are fixed).
#
# NO_VISITOR / VISITOR_DETECTED / MULTIPLE_VISITORS / GUIDE_MENU_REQUIRED /
# TOPIC_SELECTED / SESSION_COMPLETED are intentionally NOT mapped here:
# no existing RobotCommandType corresponds to them (GUIDE_MENU_REQUIRED
# is a UI concern; SESSION_COMPLETED is immediately followed by
# COOLDOWN_STARTED, which already triggers IDLE below).
_SIMPLE_EVENT_COMMAND_MAP: Dict[DecisionEventType, RobotCommandType] = {
    DecisionEventType.GREETING_REQUIRED: RobotCommandType.GREET,
    DecisionEventType.COOLDOWN_STARTED: RobotCommandType.IDLE,
    DecisionEventType.RETURN_TO_WAITING: RobotCommandType.IDLE,
    DecisionEventType.ERROR: RobotCommandType.STOP,
}

# GuideTopic -> RobotCommandType, used only for EXPLANATION_REQUIRED
# events (which carry a "topic" in their metadata). Both enums already
# define exactly these four matching members; this is a small, local,
# justified adapter — not a new shared contract.
_TOPIC_TO_EXPLAIN_COMMAND: Dict[GuideTopic, RobotCommandType] = {
    GuideTopic.AI_PROJECTS: RobotCommandType.EXPLAIN_AI,
    GuideTopic.ROBOTICS: RobotCommandType.EXPLAIN_ROBOTICS,
    GuideTopic.TRAINING: RobotCommandType.EXPLAIN_TRAINING,
    GuideTopic.LAB_INFORMATION: RobotCommandType.EXPLAIN_LAB,
}


class ApplicationIntegration:
    """
    Wires Decision, Guide, and Robot together behind a small facade.

    This class does NOT reimplement Decision's state machine, does NOT
    hold Guide content, and does NOT know about Robot's backend/SDK
    details — it only calls each module's existing public API and
    translates DecisionEvents into RobotCommands using the mappings
    above.

    Usage (hardware-free — the common case, and what tests use):
        app = ApplicationIntegration()
        results = app.handle_detection(detection_result)   # one Vision frame
        results = app.complete_greeting()
        results = app.select_topic(GuideTopic.AI_PROJECTS)
        results = app.complete_session()

    Usage (with a real/optional Vision camera + detector):
        app = ApplicationIntegration(camera=Camera(), detector=FaceDetector())
        results = app.capture_and_handle()   # reads one frame and processes it
    """

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        guide_service: Optional[GuideService] = None,
        robot_controller: Optional[RobotController] = None,
        camera: Optional[Camera] = None,
        detector: Optional[FaceDetectorInterface] = None,
    ) -> None:
        self._state_manager = state_manager if state_manager is not None else StateManager()
        self._guide_service = guide_service if guide_service is not None else GuideService()
        self._robot_controller = (
            robot_controller if robot_controller is not None else RobotController()
        )
        # Vision integration is optional: ApplicationIntegration is fully
        # usable and testable via handle_detection() alone, with zero
        # camera/hardware dependency. camera/detector are only needed
        # for capture_and_handle() (a real, live-camera convenience).
        self._camera = camera
        self._detector = detector
        logger.info("Application integration initialized")

    @property
    def state_manager(self) -> StateManager:
        """The underlying Decision StateManager (read-only access)."""
        return self._state_manager

    # ------------------------------------------------------------------
    # Public orchestration API
    # ------------------------------------------------------------------

    def handle_detection(
        self, detection_result: Optional[DetectionResult]
    ) -> List[RobotExecutionResult]:
        """
        Feed one Vision DetectionResult through Decision, and dispatch
        any resulting DecisionEvents to Robot.

        This is the primary integration entry point and requires no
        camera/hardware — `detection_result` may come from a live
        Camera + FaceDetector, or (as in tests) be constructed directly.
        """
        events = self._state_manager.process(detection_result)
        return self._dispatch(events)

    def capture_and_handle(self) -> List[RobotExecutionResult]:
        """
        Read one frame from the configured Vision camera/detector (if
        any) and feed it through the full pipeline.

        Returns an empty list — never raises — if no camera/detector was
        configured, the camera is unavailable, or a frame could not be
        read, consistent with Camera.open()/read()'s own fail-safe
        semantics (see app.vision.camera).
        """
        if self._camera is None or self._detector is None:
            logger.debug(
                "capture_and_handle() called with no Vision camera/detector configured"
            )
            return []

        if not self._camera.is_opened and not self._camera.open():
            logger.warning("Vision camera is unavailable")
            return []

        ok, frame = self._camera.read()
        if not ok or frame is None:
            logger.warning("Failed to read a frame from the Vision camera")
            return []

        detection_result = self._detector.detect(frame)
        return self.handle_detection(detection_result)

    def complete_greeting(self) -> List[RobotExecutionResult]:
        """Signal that the greeting has been physically completed."""
        events = self._state_manager.complete_greeting()
        return self._dispatch(events)

    def select_topic(self, topic: GuideTopic) -> List[RobotExecutionResult]:
        """Signal that a visitor selected a guide topic."""
        events = self._state_manager.select_topic(topic)
        return self._dispatch(events)

    def complete_session(self) -> List[RobotExecutionResult]:
        """Signal that the explanation/session has finished."""
        events = self._state_manager.complete_session()
        return self._dispatch(events)

    def reset(self) -> None:
        """Reset Decision state (e.g. to recover from ApplicationState.ERROR)."""
        self._state_manager.reset()

    # ------------------------------------------------------------------
    # Internal: DecisionEvent -> RobotCommand dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, events: List[DecisionEvent]) -> List[RobotExecutionResult]:
        results: List[RobotExecutionResult] = []
        for event in events:
            result = self._dispatch_one(event)
            if result is not None:
                results.append(result)
        return results

    def _dispatch_one(self, event: DecisionEvent) -> Optional[RobotExecutionResult]:
        try:
            if event.event_type in _SIMPLE_EVENT_COMMAND_MAP:
                command_type = _SIMPLE_EVENT_COMMAND_MAP[event.event_type]
                return self._robot_controller.execute(RobotCommand(command_type))

            if event.event_type is DecisionEventType.EXPLANATION_REQUIRED:
                return self._dispatch_explanation(event)

            logger.debug(
                "DecisionEvent %s requires no Robot action", event.event_type.value
            )
            return None
        except Exception:
            # Integration must fail safely: log with full context and
            # continue, never let one bad event crash the whole batch or
            # corrupt Decision state (Decision has already produced and
            # returned this event by the time we get here).
            logger.exception(
                "Unexpected error dispatching DecisionEvent %s", event.event_type.value
            )
            return None

    def _dispatch_explanation(self, event: DecisionEvent) -> Optional[RobotExecutionResult]:
        topic_value = event.metadata.get("topic")
        if topic_value is None:
            logger.error("EXPLANATION_REQUIRED event is missing 'topic' metadata")
            return None

        try:
            topic = GuideTopic(topic_value)
        except ValueError:
            logger.error(
                "EXPLANATION_REQUIRED event has an unrecognized topic=%r", topic_value
            )
            return None

        response = self._guide_service.get_topic_content(topic)
        if response.topic is None:
            logger.warning(
                "Guide returned an unavailable response for topic=%s", topic.value
            )
            return None

        command_type = _TOPIC_TO_EXPLAIN_COMMAND.get(topic)
        if command_type is None:
            logger.error("No Robot command mapping exists for topic=%s", topic.value)
            return None

        return self._robot_controller.execute(
            RobotCommand(command_type, text=response.spoken_text)
        )


def main() -> None:
    print(
        "AI University Lab Guide Robot — application integration layer.\n"
        "ApplicationIntegration wires Decision, Guide, and Robot together.\n"
        "Feed Vision frames in via handle_detection(detection_result), or\n"
        "provide a Camera + FaceDetector and call capture_and_handle().\n"
        "See docs/integration_contract.md for the full orchestration flow."
    )


if __name__ == "__main__":
    main()
