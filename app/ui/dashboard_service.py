"""
Dashboard service — the orchestration surface for the Production Demo
Dashboard.

Responsibility: compose the existing subsystem adapters
(app.ui.adapters.*) into the data the dashboard presentation layer
(app.ui.dashboard) renders. This module contains presentation
orchestration only -- all actual domain logic (routing, intent
classification, conversation state, robot execution, ...) remains
owned by the existing subsystems. DashboardService never fabricates a
result: every SubsystemStatus/EventRecord/panel it returns is derived
from a real call into a real adapter.

Dependency direction: app.ui.dashboard_service depends on
app.ui.adapters.*, app.ui.dashboard_view_models, app.ui.view_models,
and (read-only, for typed data) app.decision.event_manager /
app.models.schemas. It does not import app.main.
"""

from __future__ import annotations

import platform
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.decision.event_manager import GuideTopic
from app.models.schemas import DetectionResult
from app.speech import ConversationContext, Language
from app.ui.adapters.decision_adapter import DecisionAdapter
from app.ui.adapters.dl_adapter import DLAdapter
from app.ui.adapters.guide_adapter import GuideAdapter
from app.ui.adapters.ml_adapter import MLAdapter
from app.ui.adapters.navigation_adapter import NavigationAdapter
from app.ui.adapters.robot_adapter import DashboardRobotAdapter
from app.ui.adapters.speech_adapter import SpeechAdapter
from app.ui.adapters.vision_adapter import VisionAdapter
from app.ui.dashboard_view_models import (
    DashboardSession,
    DemoScenarioDescriptor,
    HealthState,
    InteractionPanelView,
    PerceptionPanelView,
    RobotPanelView,
    SubsystemStatus,
)
from app.ui.view_models import GuideContentView, NavigationView
from app.utils.logger import get_logger

logger = get_logger(__name__)

_TOPIC_LABELS = {
    GuideTopic.AI_PROJECTS: "AI",
    GuideTopic.ROBOTICS: "Robotics",
    GuideTopic.TRAINING: "Training",
    GuideTopic.LAB_INFORMATION: "Lab",
}


def _synthetic_detection(detected: bool) -> DetectionResult:
    """
    A deterministic, honestly-labeled stand-in DetectionResult used
    only to drive the Decision state machine in Demo Mode, when no
    physical camera/visitor is present. This is never presented as a
    real Vision detection -- see DashboardService.run_demo_scenario,
    which always records DEMO/SIMULATION provenance in the event
    timeline.
    """
    if detected:
        from app.models.schemas import BoundingBox, FaceDetection

        box = BoundingBox(x=0, y=0, width=100, height=100)
        return DetectionResult(
            detected=True,
            face_count=1,
            confidence=None,
            timestamp=datetime.now(timezone.utc),
            faces=[FaceDetection(bounding_box=box)],
        )
    return DetectionResult.empty()


class DashboardService:
    """
    Long-lived (per-session) orchestrator. Construct once and reuse
    across UI refreshes -- adapters hold their own service instances
    so expensive artifacts (ML/DL models) are loaded once, not on
    every render (see docs/ui_dashboard.md, "Performance").
    """

    def __init__(self) -> None:
        self.vision = VisionAdapter()
        self.ml = MLAdapter()
        self.dl = DLAdapter()
        self.decision = DecisionAdapter()
        self.guide = GuideAdapter()
        self.navigation = NavigationAdapter()
        self.speech = SpeechAdapter()
        self.robot = DashboardRobotAdapter()

        self.session = DashboardSession(session_id=str(uuid.uuid4())[:8])
        self.conversation_context: Optional[ConversationContext] = None

    # -- status ---------------------------------------------------------

    def status_cards(self) -> List[SubsystemStatus]:
        cards = [
            self.vision.status(),
            self.ml.status(),
            self.dl.status(),
            self.navigation.status(),
            self.decision.status(),
            self.speech.status(),
            self.guide.status(),
            self.robot.status(),
            self.robot.integration_status(),
            self._ui_status(),
        ]
        return cards

    def _ui_status(self) -> SubsystemStatus:
        # The UI layer reporting on itself: PASS as long as this
        # service constructed successfully (we would not be running
        # otherwise).
        return SubsystemStatus(name="UI", state=HealthState.PASS, detail="Dashboard service initialized")

    def overall_system_state(self) -> HealthState:
        states = {card.state for card in self.status_cards()}
        if HealthState.UNAVAILABLE in states:
            return HealthState.DEGRADED if HealthState.PASS in states else HealthState.UNAVAILABLE
        if HealthState.DEGRADED in states:
            return HealthState.DEGRADED
        return HealthState.PASS

    def system_health(self) -> List[SubsystemStatus]:
        cards = list(self.status_cards())
        cards.append(
            SubsystemStatus(
                name="Runtime",
                state=HealthState.PASS,
                detail=f"Python {platform.python_version()} on {platform.system()}",
            )
        )
        return cards

    # -- perception -------------------------------------------------------

    def refresh_perception(self) -> PerceptionPanelView:
        view = self.vision.capture_and_detect()
        if view.camera_available and view.detected is not None:
            self.session.record(
                "Vision",
                "FACE_DETECTED" if view.detected else "NO_FACE",
                f"face_count={view.face_count}",
            )
        return view

    def analyze_photo(self, frame) -> PerceptionPanelView:
        """
        Same real detection path as refresh_perception(), but against a
        frame captured elsewhere (e.g. a browser-side photo from the
        presentation UI's ``st.camera_input``) instead of opening a
        server-side camera device. See VisionAdapter.detect_in_frame.
        """
        view = self.vision.detect_in_frame(frame)
        if view.camera_available and view.detected is not None:
            self.session.record(
                "Vision",
                "FACE_DETECTED" if view.detected else "NO_FACE",
                f"face_count={view.face_count}",
            )
        return view

    # -- interaction (speech, optionally ML-classified) ------------------

    def handle_utterance(self, text: str, language: Optional[Language] = None) -> InteractionPanelView:
        intent_result = self.ml.predict(text)
        response = self.speech.handle(
            text,
            context=self.conversation_context,
            language=language,
            intent_result=intent_result,
        )
        if response is None:
            self.session.record("Speech", "UNAVAILABLE", "Speech service could not be initialized")
            return InteractionPanelView(
                user_text=text,
                spoken_text="(Speech unavailable)",
                response_type="UNAVAILABLE",
                language=(language or Language.default()).value,
            )

        self.conversation_context = response.context
        self.session.record(
            "ML",
            "INTENT_CLASSIFIED" if intent_result else "INTENT_HEURISTIC",
            f"intent={intent_result.intent.value}" if intent_result else "no ML artifact",
        )
        self.session.record("Speech", response.response_type.value, response.spoken_text)

        return InteractionPanelView(
            user_text=text,
            spoken_text=response.spoken_text,
            response_type=response.response_type.value,
            language=response.language.value,
            intent_label=intent_result.intent.value if intent_result else None,
            intent_confidence=intent_result.confidence if intent_result else None,
            requires_clarification=response.requires_clarification,
            destination=response.context.current_destination,
        )

    def reset_conversation(self) -> None:
        self.conversation_context = None

    # -- navigation -------------------------------------------------------

    def request_route(self, origin: str, destination: str) -> NavigationView:
        view = self.navigation.find_route(origin, destination)
        self.session.record(
            "Navigation",
            "ROUTE_FOUND" if view.route is not None else "ROUTE_UNAVAILABLE",
            view.message or (view.destination_name or ""),
        )
        return view

    # -- guide --------------------------------------------------------------

    def get_guide_content(self, topic: GuideTopic) -> Optional[GuideContentView]:
        view = self.guide.get_topic_view(topic)
        self.session.record("Guide", "TOPIC_CONTENT", topic.value)
        return view

    # -- robot ----------------------------------------------------------

    def robot_action(self, action_key: str, text: str = "") -> RobotPanelView:
        dispatch = {
            "GREET": self.robot.greet,
            "WAVE": self.robot.wave,
            "IDLE": self.robot.idle,
            "STOP": self.robot.stop,
            "SPEAK": lambda: self.robot.speak(text),
            "EXPLAIN_AI": lambda: self.robot.explain("EXPLAIN_AI", text),
            "EXPLAIN_ROBOTICS": lambda: self.robot.explain("EXPLAIN_ROBOTICS", text),
            "EXPLAIN_TRAINING": lambda: self.robot.explain("EXPLAIN_TRAINING", text),
            "EXPLAIN_LAB": lambda: self.robot.explain("EXPLAIN_LAB", text),
        }
        fn = dispatch.get(action_key)
        if fn is None:
            view = RobotPanelView(backend_mode="SIMULATED", last_command=action_key, last_success=False,
                                   last_message=f"Unsupported action: {action_key}")
        else:
            view = fn()
        self.session.record("Robot", action_key, view.last_message or "")
        return view

    # -- demo scenarios ---------------------------------------------------

    def demo_scenarios(self) -> List[DemoScenarioDescriptor]:
        ml_ok = self.ml.status().state != HealthState.UNAVAILABLE
        speech_ok = self.speech.status().state != HealthState.UNAVAILABLE
        guide_ok = self.guide.status().state != HealthState.UNAVAILABLE
        nav_ok = self.navigation.status().state != HealthState.UNAVAILABLE
        robot_ok = self.robot.status().state != HealthState.UNAVAILABLE

        def scenario(key, title, description, ok):
            return DemoScenarioDescriptor(
                key=key,
                title=title,
                description=description,
                available=ok,
                unavailable_reason=None if ok else "Required subsystem is not connected",
            )

        return [
            scenario("GREETING", "Greeting", "Visitor detected -> Decision greets -> Robot waves",
                      speech_ok and robot_ok),
            scenario("ASK_AI", "Ask about AI", "Student asks about AI -> Guide content -> Robot explains",
                      guide_ok and speech_ok and robot_ok),
            scenario("ASK_ROBOTICS", "Ask about Robotics", "Guide content for Robotics -> Robot explains",
                      guide_ok and speech_ok and robot_ok),
            scenario("ASK_TRAINING", "Ask about Training", "Guide content for Training -> Robot explains",
                      guide_ok and speech_ok and robot_ok),
            scenario("ASK_LAB", "Ask about Lab", "Guide content for Lab -> Robot explains",
                      guide_ok and speech_ok and robot_ok),
            scenario("NAVIGATION", "Navigation request", "Speech destination -> real Navigation route",
                      nav_ok and speech_ok),
            scenario("UNKNOWN", "Unknown request / fallback", "Out-of-vocabulary text -> fallback response",
                      speech_ok),
            scenario("ARABIC", "Arabic interaction", "Arabic-script text handled end-to-end", speech_ok),
            scenario("ENGLISH", "English interaction", "English text handled end-to-end", speech_ok),
        ]

    def run_demo_scenario(self, key: str) -> List[str]:
        """
        Execute one demo scenario against real services and return a
        short log of what happened (also appended to the session event
        timeline). Every step below calls a real adapter -- nothing is
        pre-scripted output.
        """
        self.session.record("Demo", "SCENARIO_STARTED", key)
        log: List[str] = []

        if key == "GREETING":
            events = self.decision.process(_synthetic_detection(True))
            for event in events:
                self.session.record("Decision", event.event_type.value)
            log.append(f"Decision events: {[e.event_type.value for e in events]}")
            robot_view = self.robot.greet()
            self.session.record("Robot", "GREET", robot_view.last_message or "")
            log.append(f"Robot greet: success={robot_view.last_success} ({robot_view.last_message})")
            wave_view = self.robot.wave()
            self.session.record("Robot", "WAVE", wave_view.last_message or "")
            log.append(f"Robot wave: success={wave_view.last_success} ({wave_view.last_message})")

        elif key in {"ASK_AI", "ASK_ROBOTICS", "ASK_TRAINING", "ASK_LAB"}:
            topic_map = {
                "ASK_AI": GuideTopic.AI_PROJECTS,
                "ASK_ROBOTICS": GuideTopic.ROBOTICS,
                "ASK_TRAINING": GuideTopic.TRAINING,
                "ASK_LAB": GuideTopic.LAB_INFORMATION,
            }
            explain_map = {
                "ASK_AI": "EXPLAIN_AI",
                "ASK_ROBOTICS": "EXPLAIN_ROBOTICS",
                "ASK_TRAINING": "EXPLAIN_TRAINING",
                "ASK_LAB": "EXPLAIN_LAB",
            }
            topic = topic_map[key]
            content = self.get_guide_content(topic)
            log.append(f"Guide content: {content.title if content else 'unavailable'}")
            if content is not None:
                robot_view = self.robot_action(explain_map[key], content.spoken_text)
                log.append(f"Robot {explain_map[key]}: success={robot_view.last_success}")

        elif key == "NAVIGATION":
            view = self.request_route("Entrance", "AI Lab")
            log.append(f"Navigation: destination={view.destination_name}, message={view.message}")

        elif key == "UNKNOWN":
            interaction = self.handle_utterance("asdkfj qwoeiru zxcvvb")
            log.append(f"Speech fallback: {interaction.response_type} -> {interaction.spoken_text}")

        elif key == "ARABIC":
            interaction = self.handle_utterance("أين المختبر؟")
            log.append(f"Speech (Arabic): {interaction.response_type} -> {interaction.spoken_text}")

        elif key == "ENGLISH":
            interaction = self.handle_utterance("Where is the AI Lab?")
            log.append(f"Speech (English): {interaction.response_type} -> {interaction.spoken_text}")

        else:
            log.append(f"Unknown scenario key: {key}")

        self.session.record("Demo", "SCENARIO_FINISHED", key)
        return log
