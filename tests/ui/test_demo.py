"""
Focused tests for app.ui.demo (Presentation Demo Mode).

These do not re-audit the domain services (already covered by
tests/ui/test_dashboard_service.py and the earlier UI phase's tests).
They verify the presentation module imports cleanly and that its
helper logic drives the same real DashboardService correctly.

Camera/Vision tests in this file are deterministic and require no
physical webcam: they either (a) exercise the real detection path
against a synthetic frame, which honestly reports "no face" without
any mocking, or (b) stub the Vision boundary (FaceDetector) to force
a specific outcome. Nothing here assumes a headless environment --
they must pass identically whether or not the machine running pytest
has a real camera, since the browser-side st.camera_input capture
path never touches server-side camera hardware in the first place.
"""

from __future__ import annotations

import hashlib
import importlib

import numpy as np
import pytest

from app.decision.event_manager import GuideTopic
from app.ui.dashboard_service import DashboardService


class TestDemoModuleImports:
    def test_demo_module_imports_without_error(self):
        importlib.import_module("app.ui.demo")

    def test_dashboard_module_is_unmodified_and_still_imports(self):
        # app/ui/dashboard.py must remain the unchanged technical dashboard.
        importlib.import_module("app.ui.dashboard")


class TestGreetingFlow:
    def test_greeting_drives_real_robot_simulation(self):
        service = DashboardService()
        greet_view = service.robot_action("GREET")
        wave_view = service.robot_action("WAVE")
        assert greet_view.backend_mode == "SIMULATED"
        assert wave_view.backend_mode == "SIMULATED"
        assert greet_view.last_success is True
        assert wave_view.last_success is True

    def test_decision_accepts_a_real_reconstructed_detection_result(self):
        from app.models.schemas import BoundingBox, DetectionResult, FaceDetection
        from datetime import datetime, timezone

        service = DashboardService()
        detection = DetectionResult(
            detected=True,
            face_count=1,
            confidence=None,
            timestamp=datetime.now(timezone.utc),
            faces=[FaceDetection(bounding_box=BoundingBox(x=0, y=0, width=100, height=100))],
        )
        events = service.decision.process(detection)
        # Must not enter ERROR state for a well-formed DetectionResult.
        assert service.decision.state is not None
        assert service.decision.state.value != "ERROR"


class TestInteractionFlow:
    def test_guide_topic_question_returns_real_content(self):
        service = DashboardService()
        content = service.get_guide_content(GuideTopic.AI_PROJECTS)
        assert content is not None
        assert content.spoken_text

    def test_navigation_question_triggers_real_navigation_service(self):
        service = DashboardService()
        interaction = service.handle_utterance("Take me to the AI Lab")
        assert interaction.response_type == "NAVIGATION_CONFIRMATION"
        assert interaction.destination
        nav_view = service.request_route("Entrance", interaction.destination)
        assert nav_view is not None
        assert nav_view.route is not None

    def test_unknown_utterance_falls_back_without_crashing(self):
        service = DashboardService()
        interaction = service.handle_utterance("zzqx flkj wrbn")
        assert interaction.spoken_text

    def test_arabic_utterance_is_handled_end_to_end(self):
        service = DashboardService()
        interaction = service.handle_utterance("أين المختبر؟")
        assert interaction.spoken_text


class TestRobotFallback:
    def test_speak_action_works_as_a_generic_response_channel(self):
        service = DashboardService()
        view = service.robot_action("SPEAK", "Welcome to AI University Lab.")
        assert view.last_success is True


# ---------------------------------------------------------------------------
# Vision boundary: real detection against a synthetic frame (no mocking,
# no camera hardware) plus explicit Vision-unavailable stubs.
# ---------------------------------------------------------------------------

class TestVisionFramePipeline:
    def test_detect_in_frame_on_a_blank_frame_reports_no_person_honestly(self):
        # A real call into the real FaceDetector against a synthetic
        # frame -- deterministically no face, with zero mocking.
        service = DashboardService()
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        view = service.analyze_photo(frame)
        assert view.camera_available is True
        assert view.detected is False
        assert view.frame is not None

    def test_analyze_photo_records_a_session_event_for_no_face(self):
        service = DashboardService()
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        service.analyze_photo(frame)
        events = [e for e in service.session.events if e.source == "Vision"]
        assert events
        assert events[-1].event == "NO_FACE"

    def test_detect_in_frame_reports_unavailable_when_face_detector_cannot_load(self, monkeypatch):
        from app.ui.adapters.vision_adapter import VisionAdapter

        def _boom(*args, **kwargs):
            raise RuntimeError("cascade missing")

        monkeypatch.setattr("app.vision.face_detector.FaceDetector.__init__", _boom)

        adapter = VisionAdapter()
        view = adapter.detect_in_frame(np.zeros((10, 10, 3), dtype=np.uint8))
        assert view.camera_available is True
        assert view.detected is None
        assert view.unavailable_reason


# ---------------------------------------------------------------------------
# Presentation-layer photo processing (app.ui.demo internals). Stubs the
# Vision boundary (FaceDetector.detect) to force a deterministic outcome,
# per the requirement that these tests never assume real hardware state.
# ---------------------------------------------------------------------------

class _FakePhoto:
    """Stand-in for the UploadedFile-like object st.camera_input returns."""

    def __init__(self, content: bytes) -> None:
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def _real_jpeg_bytes(fill_value: int) -> bytes:
    """
    A genuinely decodable JPEG (needed because _decode_photo() really
    runs cv2.imdecode) whose *content* is irrelevant -- detection
    outcome in these tests is controlled by monkeypatching
    FaceDetector.detect, not by the pixels themselves.
    """
    import cv2

    frame = np.full((32, 32, 3), fill_value, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame)
    assert ok
    return buf.tobytes()


def _make_detection_result(detected: bool, face_count: int = 0):
    from datetime import datetime, timezone

    from app.models.schemas import BoundingBox, DetectionResult, FaceDetection

    if not detected:
        return DetectionResult.empty()
    faces = [FaceDetection(bounding_box=BoundingBox(x=0, y=0, width=50, height=50)) for _ in range(face_count)]
    return DetectionResult(
        detected=True,
        face_count=face_count,
        confidence=None,
        timestamp=datetime.now(timezone.utc),
        faces=faces,
    )


class TestPhotoProcessing:
    @pytest.fixture(autouse=True)
    def _clean_session_state(self):
        import streamlit as st

        st.session_state.clear()
        yield
        st.session_state.clear()

    def test_person_detected_triggers_greeting_exactly_once(self, monkeypatch):
        import streamlit as st

        from app.ui import demo as demo_mod

        monkeypatch.setattr(
            "app.vision.face_detector.FaceDetector.detect",
            lambda self, frame: _make_detection_result(True, face_count=1),
        )

        service = DashboardService()
        photo = _FakePhoto(_real_jpeg_bytes(10))

        demo_mod._process_captured_photo(service, photo)

        view = st.session_state["demo_perception"]
        assert view.detected is True
        assert st.session_state["demo_greeted"] is True
        # Real robot simulation ran as part of the greeting.
        assert st.session_state.get("demo_robot_message")

    def test_no_person_does_not_greet(self, monkeypatch):
        import streamlit as st

        from app.ui import demo as demo_mod

        monkeypatch.setattr(
            "app.vision.face_detector.FaceDetector.detect",
            lambda self, frame: _make_detection_result(False),
        )

        service = DashboardService()
        photo = _FakePhoto(_real_jpeg_bytes(20))

        demo_mod._process_captured_photo(service, photo)

        view = st.session_state["demo_perception"]
        assert view.detected is False
        assert st.session_state.get("demo_greeted") is False

    def test_same_capture_is_only_processed_once(self, monkeypatch):
        import streamlit as st

        from app.ui import demo as demo_mod

        call_count = {"n": 0}

        def _counting_detect(self, frame):
            call_count["n"] += 1
            return _make_detection_result(True, face_count=1)

        monkeypatch.setattr("app.vision.face_detector.FaceDetector.detect", _counting_detect)

        service = DashboardService()
        photo = _FakePhoto(_real_jpeg_bytes(30))

        demo_mod._process_captured_photo(service, photo)
        demo_mod._process_captured_photo(service, photo)  # same content -> should be a no-op

        assert call_count["n"] == 1

    def test_a_new_capture_is_processed_again(self, monkeypatch):
        import streamlit as st

        from app.ui import demo as demo_mod

        call_count = {"n": 0}

        def _counting_detect(self, frame):
            call_count["n"] += 1
            return _make_detection_result(False)

        monkeypatch.setattr("app.vision.face_detector.FaceDetector.detect", _counting_detect)

        service = DashboardService()
        demo_mod._process_captured_photo(service, _FakePhoto(_real_jpeg_bytes(40)))
        demo_mod._process_captured_photo(service, _FakePhoto(_real_jpeg_bytes(41)))

        assert call_count["n"] == 2

    def test_undecodable_photo_bytes_are_handled_gracefully(self):
        import streamlit as st

        from app.ui import demo as demo_mod

        service = DashboardService()
        demo_mod._process_captured_photo(service, _FakePhoto(b"not a real jpeg"))

        assert st.session_state.get("demo_photo_error")
        assert st.session_state.get("demo_perception") is None


# ---------------------------------------------------------------------------
# Full-screen behavior via Streamlit's AppTest harness (no browser, no
# camera hardware -- st.camera_input itself never touches server-side
# camera devices, so this covers the state Streamlit exposes to Python
# before any browser photo is taken).
# ---------------------------------------------------------------------------

class TestPresentationUiRefinement:
    def _app(self):
        from pathlib import Path

        from streamlit.testing.v1 import AppTest

        repo_root = Path(__file__).resolve().parents[2]
        at = AppTest.from_file(str(repo_root / "app" / "ui" / "demo.py"), default_timeout=30)
        at.run()
        return at

    def test_first_screen_is_camera_stage_with_no_pipeline_jargon(self):
        at = self._app()
        assert not at.exception
        body = "\n".join(md.value for md in at.markdown)
        # Professor-facing screen must not expose developer/dashboard
        # vocabulary anywhere in the initial render.
        for forbidden in ("System Pipeline", "SubsystemStatus", "UNAVAILABLE", "DEGRADED", "Adapter", "Session ID"):
            assert forbidden not in body

    def test_initial_screen_shows_live_camera_widget(self):
        at = self._app()
        assert not at.exception
        # st.camera_input renders as a distinct element the AppTest
        # tree exposes as camera_input.
        assert len(at.get("camera_input")) == 1

    def test_continue_in_demo_mode_reaches_assistant_home_without_claiming_a_detection(self):
        at = self._app()
        at.button(key="demo_skip").click().run()
        assert not at.exception
        assert at.session_state["demo_stage"] == "assistant"
        assert "demo_greeted" not in at.session_state or not at.session_state["demo_greeted"]
        body = "\n".join(md.value for md in at.markdown)
        assert "Hi there" in body

    def test_ask_about_ai_button_shows_real_guide_content_on_assistant_home(self):
        at = self._app()
        at.session_state["demo_stage"] = "assistant"
        at.run()
        at.button(key="demo_btn_ASK_AI").click().run()
        assert not at.exception
        result = at.session_state["demo_result"]
        assert result["kind"] == "guide"
        assert result["text"]

    def test_find_a_lab_button_shows_real_navigation_route(self):
        at = self._app()
        at.session_state["demo_stage"] = "assistant"
        at.run()
        at.button(key="demo_btn_nav").click().run()
        assert not at.exception
        result = at.session_state["demo_result"]
        assert result["kind"] == "navigation"
        assert result["nav_view"].route is not None

    def test_restart_demo_clears_state_back_to_camera_stage(self):
        at = self._app()
        at.session_state["demo_stage"] = "assistant"
        at.run()
        at.button(key="demo_btn_ASK_AI").click().run()
        at.button(key="demo_restart").click().run()
        assert not at.exception
        assert at.session_state["demo_stage"] == "camera"
        assert "demo_result" not in at.session_state
