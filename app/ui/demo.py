"""
AI University Lab Guide -- Presentation Demo.

A polished, professor-facing presentation screen built ON TOP OF the
existing app.ui.dashboard_service.DashboardService and its adapters.
This module is a thin presentation layer only: it holds no business
logic, reimplements no domain service, and never fabricates data.
Everything shown comes from the same real services the technical
dashboard (app/ui/dashboard.py, unchanged) uses.

Screen flow (a small presentation-only state machine kept in
st.session_state["demo_stage"]):

    CAMERA -> GREETING -> ASSISTANT (interaction / result, looped)

Launch:

    python -m streamlit run app/ui/demo.py
"""

from __future__ import annotations

import hashlib

import cv2
import numpy as np
import streamlit as st

from app.decision.event_manager import GuideTopic
from app.models.schemas import DetectionResult
from app.speech.language import Language
from app.speech.response import ConversationResponseType
from app.ui.dashboard_service import DashboardService

st.set_page_config(
    page_title="AI University Lab Guide",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

_TOPIC_KEYS = {
    "ASK_AI": (GuideTopic.AI_PROJECTS, "EXPLAIN_AI", "🧠", "Ask about AI"),
    "ASK_ROBOTICS": (GuideTopic.ROBOTICS, "EXPLAIN_ROBOTICS", "🤖", "Ask about Robotics"),
    "ASK_TRAINING": (GuideTopic.TRAINING, "EXPLAIN_TRAINING", "🎯", "Ask about Training"),
}

_ROBOT_FRIENDLY = {
    "GREET": "Welcoming you",
    "WAVE": "Waving hello",
    "SPEAK": "Speaking",
    "EXPLAIN_AI": "Explaining",
    "EXPLAIN_ROBOTICS": "Explaining",
    "EXPLAIN_TRAINING": "Explaining",
    "EXPLAIN_LAB": "Explaining",
    "IDLE": "Idle",
    "STOP": "Stopped",
}


# ---------------------------------------------------------------------------
# Visual theme (presentation-layer only -- no business logic lives here)
# ---------------------------------------------------------------------------

def _inject_style() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        #MainMenu, header, footer { visibility: hidden; }

        .stApp {
            background: radial-gradient(circle at 20% 0%, #1b2440 0%, #0b1020 45%, #070a15 100%);
            color: #e7ebff;
        }

        .block-container { padding-top: 2.2rem; max-width: 760px; }

        .lab-title {
            text-align: center;
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: 0.5px;
            margin-bottom: 0.1rem;
            background: linear-gradient(90deg, #7c9dff, #b98bff 60%, #ff9ecb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .lab-subtitle {
            text-align: center;
            color: #97a2c9;
            font-size: 1.02rem;
            margin-bottom: 1.6rem;
        }

        .lab-card {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 18px;
            padding: 1.6rem 1.6rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }
        .lab-card.center { text-align: center; }

        .lab-pill {
            display: inline-block;
            padding: 0.32rem 0.9rem;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.6rem;
        }
        .pill-waiting { background: rgba(124,157,255,0.15); color: #9db3ff; }
        .pill-success { background: rgba(63,209,150,0.15); color: #5be3ab; }
        .pill-warn    { background: rgba(255,178,80,0.15); color: #ffc16b; }

        .camera-frame {
            width: 100%;
            max-width: 320px;
            aspect-ratio: 1 / 1;
            margin: 0.4rem auto 1rem auto;
            border-radius: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3.4rem;
            background: radial-gradient(circle, #202a4d 0%, #131a30 100%);
            border: 2px dashed rgba(124,157,255,0.45);
        }
        .camera-frame.found {
            border: 2px solid #5be3ab;
            background: radial-gradient(circle, #16352a 0%, #0f1f1a 100%);
        }

        .lab-h {
            font-weight: 700;
            font-size: 1.15rem;
            margin-bottom: 0.3rem;
            color: #f1f3ff;
        }
        .lab-muted { color: #9aa4cc; font-size: 0.92rem; }

        .robot-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.95rem;
            color: #cfd6ff;
            background: rgba(124,157,255,0.08);
            border-radius: 12px;
            padding: 0.55rem 0.9rem;
            margin-top: 0.6rem;
        }

        .route-chain { margin-top: 0.6rem; }
        .route-node {
            background: rgba(124,157,255,0.10);
            border: 1px solid rgba(124,157,255,0.25);
            border-radius: 12px;
            padding: 0.55rem 0.9rem;
            font-weight: 600;
            color: #eef1ff;
            margin-bottom: 0.15rem;
        }
        .route-node.origin { background: rgba(255,255,255,0.05); color: #b7c0ea; font-weight: 500; }
        .route-node.dest { background: rgba(91,227,171,0.12); border-color: rgba(91,227,171,0.4); color: #7ff0c4; }
        .route-arrow { text-align: center; color: #7c9dff; margin: -0.05rem 0; }

        .rtl-text {
            direction: rtl;
            text-align: right;
            font-size: 1.05rem;
            line-height: 1.7;
        }

        div[data-testid="stButton"] > button {
            border-radius: 12px;
            font-weight: 600;
            border: 1px solid rgba(124,157,255,0.35);
        }
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(90deg, #6f8dff, #9c7dff);
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Service / session plumbing
# ---------------------------------------------------------------------------

@st.cache_resource
def get_service() -> DashboardService:
    # Its own DashboardService instance (own process from dashboard.py),
    # constructed once per session so ML/DL/Guide/Navigation/Speech/
    # Robot services are not rebuilt on every widget interaction.
    return DashboardService()


def _stage() -> str:
    return st.session_state.setdefault("demo_stage", "camera")


def _go(stage: str) -> None:
    st.session_state["demo_stage"] = stage


def _set_robot_status(action_key: str, message: str | None) -> None:
    friendly = _ROBOT_FRIENDLY.get(action_key, action_key.title())
    st.session_state["demo_robot_status"] = friendly
    st.session_state["demo_robot_message"] = message or ""


def render_header() -> None:
    st.markdown('<div class="lab-title">AI UNIVERSITY LAB GUIDE</div>', unsafe_allow_html=True)
    st.markdown('<div class="lab-subtitle">Your Intelligent Lab Assistant</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Screen 1 -- Camera / Welcome
# ---------------------------------------------------------------------------

def _decode_photo(photo_bytes: bytes) -> "np.ndarray | None":
    """
    Decode a JPEG captured by Streamlit's browser-side st.camera_input
    into a BGR frame the real FaceDetector can consume. Returns None
    (never raises) if the bytes can't be decoded.
    """
    try:
        array = np.frombuffer(photo_bytes, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        return frame
    except Exception:
        return None


def _process_captured_photo(service: DashboardService, photo) -> None:
    """
    Run real detection on a newly captured browser photo exactly once
    per capture (guarded by a content hash so Streamlit reruns caused
    by *other* widgets on this screen never re-run detection or
    re-trigger the robot greeting for the same photo).
    """
    photo_bytes = photo.getvalue()
    signature = hashlib.md5(photo_bytes).hexdigest()
    if st.session_state.get("demo_photo_signature") == signature:
        return  # already processed this exact capture

    st.session_state["demo_photo_signature"] = signature
    st.session_state["demo_greeted"] = False

    frame = _decode_photo(photo_bytes)
    if frame is None:
        st.session_state["demo_perception"] = None
        st.session_state["demo_photo_error"] = "Could not read the captured photo. Please try again."
        return

    st.session_state["demo_photo_error"] = None
    view = service.analyze_photo(frame)
    st.session_state["demo_perception"] = view
    if view.camera_available and view.detected:
        _greet(service, view)


def _greet(service: DashboardService, perception_view=None) -> None:
    # Drive the real Decision state machine with the real DetectionResult
    # fields already returned by Vision (reconstructed here only because
    # DashboardService.refresh_perception exposes a display view, not
    # the raw domain object -- detected/face_count/confidence/timestamp
    # are never invented; only placeholder bounding boxes are added
    # because PerceptionPanelView does not carry them, to satisfy
    # DetectionResult's len(faces) == face_count invariant).
    if perception_view is not None and perception_view.detected is not None:
        from app.models.schemas import BoundingBox, FaceDetection

        face_count = perception_view.face_count or 0
        faces = [
            FaceDetection(bounding_box=BoundingBox(x=0, y=0, width=100, height=100))
            for _ in range(face_count)
        ]
        detection = DetectionResult(
            detected=perception_view.detected,
            face_count=face_count,
            confidence=perception_view.confidence,
            timestamp=perception_view.timestamp,
            faces=faces,
        )
        service.decision.process(detection)
    st.session_state["demo_greeted"] = True
    robot_view = service.robot_action("GREET")
    wave_view = service.robot_action("WAVE")
    _set_robot_status("WAVE", wave_view.last_message)


def _camera_widget_key() -> str:
    # A fresh key (bumped by Restart Demo) forces Streamlit to render a
    # brand-new st.camera_input with no captured photo, rather than
    # trying to programmatically clear one.
    epoch = st.session_state.setdefault("demo_camera_epoch", 0)
    return f"demo_camera_input_{epoch}"


def render_camera_screen(service: DashboardService) -> None:
    st.markdown('<div class="lab-card center">', unsafe_allow_html=True)
    st.markdown('<div class="lab-h">Look at the camera</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="lab-muted">Your browser will open a live camera preview below -- '
        'take a photo when you\'re ready and the assistant will look for you.</div>',
        unsafe_allow_html=True,
    )

    # Real, browser-side live camera preview (Streamlit's native
    # camera widget). This is the actual fix for "the LED turns on but
    # I never see the feed": a server-side cv2 grab has no browser
    # display path, but st.camera_input renders a genuine live
    # viewfinder in the presenter's own browser before any capture.
    photo = st.camera_input(
        "Camera",
        key=_camera_widget_key(),
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="lab-card center">', unsafe_allow_html=True)

    if photo is None:
        st.markdown('<span class="lab-pill pill-waiting">● Looking for you...</span>', unsafe_allow_html=True)
        st.markdown('<div class="lab-muted">Please look at the camera and press the capture button above.</div>', unsafe_allow_html=True)
        st.write("")
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if st.button("Continue in Demo Mode →", key="demo_skip", use_container_width=True):
                _go("assistant")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    _process_captured_photo(service, photo)

    error = st.session_state.get("demo_photo_error")
    view = st.session_state.get("demo_perception")

    if error:
        st.markdown('<span class="lab-pill pill-warn">⚠ Couldn\'t process photo</span>', unsafe_allow_html=True)
        st.markdown(f'<div class="lab-muted">{error}</div>', unsafe_allow_html=True)
        st.write("")
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if st.button("Continue in Demo Mode →", key="demo_skip_err", type="primary", use_container_width=True):
                _go("assistant")
                st.rerun()

    elif view is not None and not view.camera_available:
        st.markdown('<span class="lab-pill pill-warn">⚠ Camera unavailable</span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="lab-muted">Camera access is unavailable. '
            f'({view.unavailable_reason or "No camera detected"})</div>',
            unsafe_allow_html=True,
        )
        st.write("")
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if st.button("Continue in Demo Mode →", key="demo_skip2", type="primary", use_container_width=True):
                _go("assistant")
                st.rerun()

    elif view is not None and not view.detected:
        st.markdown('<span class="lab-pill pill-warn">○ No person detected</span>', unsafe_allow_html=True)
        st.markdown(
            '<div class="lab-muted">I can\'t see you yet. Please look toward the camera '
            'and retake the photo above.</div>',
            unsafe_allow_html=True,
        )
        st.write("")
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if st.button("Continue in Demo Mode →", key="demo_skip3", use_container_width=True):
                _go("assistant")
                st.rerun()

    elif view is not None and view.detected:
        st.markdown('<span class="lab-pill pill-success">✓ Person detected</span>', unsafe_allow_html=True)
        st.markdown('<div class="lab-h">Welcome! It\'s great to see you.</div>', unsafe_allow_html=True)
        robot_msg = st.session_state.get("demo_robot_message") or "Waving hello"
        st.markdown(f'<div class="robot-status">🤖 &nbsp;{robot_msg}</div>', unsafe_allow_html=True)
        st.write("")
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if st.button("Continue →", key="demo_continue", type="primary", use_container_width=True):
                _go("assistant")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Screen 2 -- Assistant home / interaction / result
# ---------------------------------------------------------------------------

def _ask_topic(service: DashboardService, key: str) -> None:
    topic, explain_action, _icon, _label = _TOPIC_KEYS[key]
    content = service.get_guide_content(topic)
    if content is not None:
        robot_view = service.robot_action(explain_action, content.spoken_text)
        _set_robot_status(explain_action, robot_view.last_message)
        st.session_state["demo_result"] = {
            "kind": "guide",
            "title": content.title,
            "text": content.spoken_text,
            "sections": content.sections,
        }
    else:
        st.session_state["demo_result"] = {"kind": "unavailable", "text": "That information isn't available right now."}


def _ask(service: DashboardService, text: str) -> None:
    interaction = service.handle_utterance(text)

    if interaction.response_type == ConversationResponseType.NAVIGATION_CONFIRMATION.value and interaction.destination:
        nav_view = service.request_route("Entrance", interaction.destination)
        robot_view = service.robot_action("SPEAK", interaction.spoken_text)
        _set_robot_status("SPEAK", robot_view.last_message)
        st.session_state["demo_result"] = {
            "kind": "navigation",
            "spoken_text": interaction.spoken_text,
            "nav_view": nav_view,
            "language": interaction.language,
        }
    else:
        robot_view = service.robot_action("SPEAK", interaction.spoken_text)
        _set_robot_status("SPEAK", robot_view.last_message)
        st.session_state["demo_result"] = {
            "kind": "speech",
            "spoken_text": interaction.spoken_text,
            "language": interaction.language,
        }


def render_welcome_card() -> None:
    st.markdown('<div class="lab-card">', unsafe_allow_html=True)
    if st.session_state.get("demo_greeted"):
        st.markdown('<div class="lab-h">👋 Welcome! It\'s great to see you.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="lab-h">👋 Hi there!</div>', unsafe_allow_html=True)
    st.markdown('<div class="lab-muted">How can I help you today?</div>', unsafe_allow_html=True)
    status = st.session_state.get("demo_robot_status")
    if status:
        st.markdown(f'<div class="robot-status">🤖 &nbsp;{status}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_actions(service: DashboardService) -> None:
    st.markdown('<div class="lab-card">', unsafe_allow_html=True)
    st.markdown('<div class="lab-h">Ask the assistant</div>', unsafe_allow_html=True)

    text = st.text_input(
        "Ask a question",
        value="",
        placeholder="Take me to the AI Lab",
        key="demo_text",
        label_visibility="collapsed",
    )
    if st.button("Ask →", key="demo_ask", type="primary") and text.strip():
        _ask(service, text)

    st.markdown('<div class="lab-muted" style="margin-top:0.9rem;">Or try a quick demo:</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    for col, key in zip(cols, ("ASK_AI", "ASK_ROBOTICS", "ASK_TRAINING")):
        _icon_label = f"{_TOPIC_KEYS[key][2]} {_TOPIC_KEYS[key][3]}"
        if col.button(_icon_label, key=f"demo_btn_{key}", use_container_width=True):
            _ask_topic(service, key)

    cols2 = st.columns(2)
    if cols2[0].button("🧭 Find a Lab", key="demo_btn_nav", use_container_width=True):
        _ask(service, "Take me to the AI Lab")
    if cols2[1].button("🌐 Arabic Demo", key="demo_btn_arabic", use_container_width=True):
        _ask(service, "أين المختبر؟")

    st.markdown("</div>", unsafe_allow_html=True)


def render_result() -> None:
    result = st.session_state.get("demo_result")
    if result is None:
        return

    st.markdown('<div class="lab-card">', unsafe_allow_html=True)

    if result["kind"] == "guide":
        st.markdown(f'<div class="lab-h">{result["title"]}</div>', unsafe_allow_html=True)
        st.write(result["text"])
        for section in result.get("sections") or []:
            st.markdown(f"- {section}")

    elif result["kind"] == "navigation":
        st.markdown('<div class="lab-h">🧭 Navigation</div>', unsafe_allow_html=True)
        is_ar = result.get("language") == Language.ARABIC.value
        spoken = f'<div class="rtl-text">{result["spoken_text"]}</div>' if is_ar else f'<div>{result["spoken_text"]}</div>'
        st.markdown(spoken, unsafe_allow_html=True)

        nav_view = result["nav_view"]
        if nav_view.route is not None:
            st.markdown('<div class="route-chain">', unsafe_allow_html=True)
            st.markdown('<div class="route-node origin">📍 You are here</div>', unsafe_allow_html=True)
            st.markdown('<div class="route-arrow">↓</div>', unsafe_allow_html=True)
            steps = nav_view.route.steps
            for step in steps:
                st.markdown(f'<div class="route-node">{step.instruction}</div>', unsafe_allow_html=True)
                st.markdown('<div class="route-arrow">↓</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="route-node dest">🎯 {nav_view.route.destination_name}</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning(nav_view.message or "I couldn't find a route to that location.")

    elif result["kind"] == "speech":
        st.markdown('<div class="lab-h">💬 Assistant</div>', unsafe_allow_html=True)
        is_ar = result.get("language") == Language.ARABIC.value
        spoken = f'<div class="rtl-text">{result["spoken_text"]}</div>' if is_ar else f'<div>{result["spoken_text"]}</div>'
        st.markdown(spoken, unsafe_allow_html=True)

    elif result["kind"] == "unavailable":
        st.warning(result["text"])

    st.markdown("</div>", unsafe_allow_html=True)


def render_footer() -> None:
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("↻ Restart Demo", key="demo_restart", use_container_width=True):
            for key in (
                "demo_stage", "demo_perception", "demo_greeted", "demo_robot_status",
                "demo_robot_message", "demo_result", "demo_text",
                "demo_photo_signature", "demo_photo_error",
            ):
                st.session_state.pop(key, None)
            # Bump the camera widget key so a fresh st.camera_input
            # renders with no leftover captured photo.
            st.session_state["demo_camera_epoch"] = st.session_state.get("demo_camera_epoch", 0) + 1
            st.rerun()
    st.markdown(
        '<div class="lab-muted" style="text-align:center; margin-top:0.6rem;">'
        'Running on real project services with a simulated robot backend.</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    _inject_style()
    service = get_service()

    render_header()

    if _stage() == "camera":
        render_camera_screen(service)
    else:
        render_welcome_card()
        render_actions(service)
        render_result()

    render_footer()


if __name__ == "__main__":
    main()
