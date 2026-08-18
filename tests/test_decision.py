"""
Tests for app.decision (StateManager / event_manager).

These tests use ONLY synthetic app.models.schemas.DetectionResult
instances. They require no camera, no OpenCV, no Robot, no Robot SDK,
no UI, no Guide service, no database, and no network access.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import CONFIG
from app.decision.event_manager import (
    ApplicationState,
    DecisionEventType,
    GuideTopic,
)
from app.decision.state_manager import StateManager
from app.models.schemas import BoundingBox, DetectionResult, FaceDetection

BASE_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_result(
    face_count: int,
    t: datetime = BASE_TIME,
) -> DetectionResult:
    """Build a synthetic DetectionResult with `face_count` faces."""
    if face_count == 0:
        return DetectionResult.empty(timestamp=t)
    faces = [
        FaceDetection(bounding_box=BoundingBox(x=i * 10, y=0, width=20, height=20))
        for i in range(face_count)
    ]
    return DetectionResult(
        detected=True,
        face_count=face_count,
        confidence=None,
        timestamp=t,
        faces=faces,
    )


def frames_required() -> int:
    return CONFIG.vision.detection_frames_required


def lost_frames_required() -> int:
    return CONFIG.decision.visitor_lost_frames_required


def cooldown_seconds() -> float:
    return CONFIG.decision.greeting_cooldown_seconds


def drive_to_greeting(manager: StateManager, start: datetime = BASE_TIME) -> datetime:
    """Feed enough stable single-visitor frames to reach GREETING. Returns last timestamp used."""
    t = start
    events = []
    for i in range(frames_required()):
        t = start + timedelta(seconds=i)
        events = manager.process(make_result(1, t))
    assert manager.state is ApplicationState.GREETING
    return t


def drive_to_cooldown(manager: StateManager, start: datetime = BASE_TIME) -> datetime:
    """Drive a full session (WAITING -> ... -> COOLDOWN). Returns the cooldown-start timestamp."""
    t = drive_to_greeting(manager, start)
    t = t + timedelta(seconds=1)
    manager.complete_greeting(timestamp=t)
    t = t + timedelta(seconds=1)
    manager.select_topic(GuideTopic.AI_PROJECTS, timestamp=t)
    t = t + timedelta(seconds=1)
    manager.complete_session(timestamp=t)
    assert manager.state is ApplicationState.COOLDOWN
    return t


# ----------------------------------------------------------------------
# 1. Initial state
# ----------------------------------------------------------------------

class TestInitialState:
    def test_initial_state_is_waiting(self):
        manager = StateManager()
        assert manager.state is ApplicationState.WAITING


# ----------------------------------------------------------------------
# 2-4. Detection stability
# ----------------------------------------------------------------------

class TestDetectionStability:
    def test_no_visitor_keeps_waiting(self):
        manager = StateManager()
        for i in range(5):
            manager.process(make_result(0, BASE_TIME + timedelta(seconds=i)))
        assert manager.state is ApplicationState.WAITING

    def test_single_frame_does_not_trigger_greeting(self):
        manager = StateManager()
        assert frames_required() > 1  # sanity check on default config
        manager.process(make_result(1, BASE_TIME))
        assert manager.state is ApplicationState.WAITING

    def test_unstable_detection_does_not_trigger_greeting(self):
        manager = StateManager()
        # detected, not-detected, detected -> streak resets each miss
        manager.process(make_result(1, BASE_TIME))
        manager.process(make_result(0, BASE_TIME + timedelta(seconds=1)))
        manager.process(make_result(1, BASE_TIME + timedelta(seconds=2)))
        assert manager.state is ApplicationState.WAITING

    def test_stable_detection_emits_visitor_detected(self):
        manager = StateManager()
        all_events = []
        for i in range(frames_required()):
            all_events.extend(
                manager.process(make_result(1, BASE_TIME + timedelta(seconds=i)))
            )
        types = [e.event_type for e in all_events]
        assert DecisionEventType.VISITOR_DETECTED in types

    def test_stable_detection_transitions_to_greeting(self):
        manager = StateManager()
        drive_to_greeting(manager)
        assert manager.state is ApplicationState.GREETING


# ----------------------------------------------------------------------
# 5-8. Greeting / guide menu flow
# ----------------------------------------------------------------------

class TestGreetingFlow:
    def test_greeting_required_emitted_once_per_session(self):
        manager = StateManager()
        t = BASE_TIME
        greeting_required_count = 0
        for i in range(frames_required() + 3):
            events = manager.process(make_result(1, BASE_TIME + timedelta(seconds=i)))
            greeting_required_count += sum(
                1 for e in events if e.event_type == DecisionEventType.GREETING_REQUIRED
            )
        assert greeting_required_count == 1

    def test_complete_greeting_transitions_to_guide_menu(self):
        manager = StateManager()
        t = drive_to_greeting(manager)
        events = manager.complete_greeting(timestamp=t + timedelta(seconds=1))
        assert manager.state is ApplicationState.GUIDE_MENU
        assert any(
            e.event_type == DecisionEventType.GUIDE_MENU_REQUIRED for e in events
        )

    def test_complete_greeting_ignored_in_wrong_state(self):
        manager = StateManager()
        events = manager.complete_greeting()
        assert events == []
        assert manager.state is ApplicationState.WAITING


# ----------------------------------------------------------------------
# 9-10. Topic selection
# ----------------------------------------------------------------------

class TestTopicSelection:
    def test_select_topic_works(self):
        manager = StateManager()
        t = drive_to_greeting(manager)
        manager.complete_greeting(timestamp=t + timedelta(seconds=1))
        events = manager.select_topic(
            GuideTopic.ROBOTICS, timestamp=t + timedelta(seconds=2)
        )
        assert manager.state is ApplicationState.EXPLAINING
        assert any(e.event_type == DecisionEventType.TOPIC_SELECTED for e in events)
        assert any(
            e.event_type == DecisionEventType.EXPLANATION_REQUIRED for e in events
        )

    def test_invalid_topic_handled_safely(self):
        manager = StateManager()
        t = drive_to_greeting(manager)
        manager.complete_greeting(timestamp=t + timedelta(seconds=1))
        events = manager.select_topic("NOT_A_TOPIC")  # type: ignore[arg-type]
        assert events == []
        assert manager.state is ApplicationState.GUIDE_MENU

    def test_select_topic_ignored_in_wrong_state(self):
        manager = StateManager()
        events = manager.select_topic(GuideTopic.TRAINING)
        assert events == []
        assert manager.state is ApplicationState.WAITING


# ----------------------------------------------------------------------
# 11-12. Explanation flow
# ----------------------------------------------------------------------

class TestExplanationFlow:
    def test_explaining_state_reached(self):
        manager = StateManager()
        t = drive_to_greeting(manager)
        manager.complete_greeting(timestamp=t + timedelta(seconds=1))
        manager.select_topic(GuideTopic.LAB_INFORMATION, timestamp=t + timedelta(seconds=2))
        assert manager.state is ApplicationState.EXPLAINING

    def test_explanation_required_emitted_on_topic_selection(self):
        manager = StateManager()
        t = drive_to_greeting(manager)
        manager.complete_greeting(timestamp=t + timedelta(seconds=1))
        events = manager.select_topic(
            GuideTopic.AI_PROJECTS, timestamp=t + timedelta(seconds=2)
        )
        assert any(
            e.event_type == DecisionEventType.EXPLANATION_REQUIRED for e in events
        )


# ----------------------------------------------------------------------
# 13-14. Cooldown
# ----------------------------------------------------------------------

class TestCooldown:
    def test_session_completion_starts_cooldown(self):
        manager = StateManager()
        events = None
        t = drive_to_greeting(manager)
        manager.complete_greeting(timestamp=t + timedelta(seconds=1))
        manager.select_topic(GuideTopic.AI_PROJECTS, timestamp=t + timedelta(seconds=2))
        events = manager.complete_session(timestamp=t + timedelta(seconds=3))
        assert manager.state is ApplicationState.COOLDOWN
        assert any(e.event_type == DecisionEventType.SESSION_COMPLETED for e in events)
        assert any(e.event_type == DecisionEventType.COOLDOWN_STARTED for e in events)

    def test_repeated_detection_during_cooldown_does_not_retrigger_greeting(self):
        manager = StateManager()
        t = drive_to_cooldown(manager)
        # Same visitor keeps being detected during cooldown.
        for i in range(1, 10):
            events = manager.process(make_result(1, t + timedelta(seconds=i)))
            assert all(
                e.event_type != DecisionEventType.GREETING_REQUIRED for e in events
            )
        assert manager.state is ApplicationState.COOLDOWN


# ----------------------------------------------------------------------
# 15-16. Visitor-lost stability / return to waiting
# ----------------------------------------------------------------------

class TestVisitorLostAndReturn:
    def test_cooldown_requires_both_time_and_absence(self):
        manager = StateManager()
        t = drive_to_cooldown(manager)
        # Visitor absent but not enough time elapsed yet.
        short_step = 0.1
        for i in range(1, lost_frames_required() + 2):
            t2 = t + timedelta(seconds=i * short_step)
            manager.process(make_result(0, t2))
        assert manager.state is ApplicationState.COOLDOWN

    def test_visitor_eventually_returns_to_waiting(self):
        manager = StateManager()
        t = drive_to_cooldown(manager)
        all_events = []
        # Advance both wall-clock (via timestamps) and absence-frame count
        # past both configured thresholds.
        step = max(cooldown_seconds() / lost_frames_required(), 1.0) + 1.0
        for i in range(1, lost_frames_required() + 3):
            t2 = t + timedelta(seconds=i * step)
            all_events.extend(manager.process(make_result(0, t2)))
        assert manager.state is ApplicationState.WAITING
        all_types = [e.event_type for e in all_events]
        assert DecisionEventType.RETURN_TO_WAITING in all_types

    def test_new_visitor_after_return_to_waiting_triggers_new_session(self):
        manager = StateManager()
        t = drive_to_cooldown(manager)
        step = max(cooldown_seconds() / lost_frames_required(), 1.0) + 1.0
        for i in range(1, lost_frames_required() + 3):
            manager.process(make_result(0, t + timedelta(seconds=i * step)))
        assert manager.state is ApplicationState.WAITING

        t2 = t + timedelta(seconds=1000)
        drive_to_greeting(manager, start=t2)
        assert manager.state is ApplicationState.GREETING


# ----------------------------------------------------------------------
# 17. Multiple visitors
# ----------------------------------------------------------------------

class TestMultipleVisitors:
    def test_multiple_visitors_emits_event(self):
        manager = StateManager()
        events = manager.process(make_result(3, BASE_TIME))
        types = [e.event_type for e in events]
        assert DecisionEventType.MULTIPLE_VISITORS in types

    def test_multiple_visitors_can_still_reach_greeting(self):
        manager = StateManager()
        t = BASE_TIME
        for i in range(frames_required()):
            manager.process(make_result(2, BASE_TIME + timedelta(seconds=i)))
        assert manager.state is ApplicationState.GREETING


# ----------------------------------------------------------------------
# 18-19. Invalid input / unexpected transitions
# ----------------------------------------------------------------------

class TestInvalidInputHandling:
    def test_none_detection_result_handled_safely(self):
        manager = StateManager()
        events = manager.process(None)  # type: ignore[arg-type]
        assert manager.state is ApplicationState.ERROR
        assert any(e.event_type == DecisionEventType.ERROR for e in events)

    def test_malformed_detection_result_handled_safely(self):
        manager = StateManager()
        events = manager.process("not a detection result")  # type: ignore[arg-type]
        assert manager.state is ApplicationState.ERROR
        assert any(e.event_type == DecisionEventType.ERROR for e in events)

    def test_reset_recovers_from_error(self):
        manager = StateManager()
        manager.process(None)  # type: ignore[arg-type]
        assert manager.state is ApplicationState.ERROR
        manager.reset()
        assert manager.state is ApplicationState.WAITING

    def test_unexpected_transitions_do_not_corrupt_state(self):
        manager = StateManager()
        # Calling completion signals out of order must not crash or
        # silently advance the state machine.
        manager.complete_session()
        manager.select_topic(GuideTopic.TRAINING)
        manager.complete_greeting()
        assert manager.state is ApplicationState.WAITING


# ----------------------------------------------------------------------
# 20-22. Independence from Robot / Camera / Vision implementation
# ----------------------------------------------------------------------

class TestIndependence:
    def test_state_manager_module_has_no_robot_import(self):
        import app.decision.state_manager as mod

        source = open(mod.__file__).read()
        assert "app.robot" not in source
        assert "import robot" not in source

    def test_state_manager_module_has_no_vision_import(self):
        import app.decision.state_manager as mod

        source = open(mod.__file__).read()
        assert "app.vision" not in source
        assert "import cv2" not in source

    def test_decision_works_with_only_synthetic_data(self):
        # This entire test file only ever constructs DetectionResult
        # objects directly — no camera, no cv2, no Robot. If we reached
        # this point, that guarantee held for the whole suite.
        manager = StateManager()
        drive_to_greeting(manager)
        assert manager.state is ApplicationState.GREETING
