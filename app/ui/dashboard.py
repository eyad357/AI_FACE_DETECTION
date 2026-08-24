"""
AI University Lab Guide — Production Demo Dashboard.

A presentation-ready Streamlit control-center over the existing,
already-integrated project services. This module contains
presentation code ONLY -- all data comes from
app.ui.dashboard_service.DashboardService, which in turn only calls
real, existing application adapters/services. No fake metrics, no
fabricated detections, no invented robot capabilities.

Launch:

    streamlit run app/ui/dashboard.py

(run from the repository root, with dependencies from
requirements.txt installed).
"""

from __future__ import annotations

import streamlit as st

from app.decision.event_manager import GuideTopic
from app.speech import Language
from app.ui.dashboard_service import DashboardService
from app.ui.dashboard_view_models import HealthState

st.set_page_config(
    page_title="AI University Lab Guide — Control Dashboard",
    page_icon="🎓",
    layout="wide",
)

_STATE_COLOR = {
    HealthState.PASS: "🟢",
    HealthState.DEGRADED: "🟡",
    HealthState.UNAVAILABLE: "🔴",
}

_TOPIC_BY_KEY = {
    "ASK_AI": GuideTopic.AI_PROJECTS,
    "ASK_ROBOTICS": GuideTopic.ROBOTICS,
    "ASK_TRAINING": GuideTopic.TRAINING,
    "ASK_LAB": GuideTopic.LAB_INFORMATION,
}


@st.cache_resource
def get_service() -> DashboardService:
    # Cached across reruns within a session so ML/DL artifacts, the
    # Guide/Navigation/Speech/Robot services, etc. are constructed
    # exactly once per browser session, not on every widget interaction.
    return DashboardService()


def render_header(service: DashboardService) -> None:
    overall = service.overall_system_state()
    st.markdown("### AI UNIVERSITY LAB GUIDE")
    st.caption("AI + Robotics Integrated Control Dashboard")
    cols = st.columns([2, 2, 2])
    with cols[0]:
        st.metric("System", f"{_STATE_COLOR[overall]} {overall.value}")
    with cols[1]:
        st.metric("Session", service.session.session_id)
    with cols[2]:
        st.metric("Started", service.session.started_at.strftime("%H:%M:%S UTC"))


def render_status_cards(service: DashboardService) -> None:
    st.markdown("#### Subsystem Status")
    cards = service.status_cards()
    row1, row2 = cards[:5], cards[5:]
    for row in (row1, row2):
        cols = st.columns(len(row))
        for col, card in zip(cols, row):
            with col:
                st.metric(card.name, f"{_STATE_COLOR[card.state]} {card.state.value}")
                if card.detail:
                    st.caption(card.detail)


def render_perception_panel(service: DashboardService) -> None:
    st.markdown("##### Camera / Perception")
    if st.button("Capture frame", key="capture_frame"):
        st.session_state["perception_view"] = service.refresh_perception()

    view = st.session_state.get("perception_view")
    if view is None:
        st.info("No capture yet this session. Click 'Capture frame' to run real detection.")
        return

    if not view.camera_available:
        st.warning(f"Camera unavailable: {view.unavailable_reason}")
        return

    if view.detected is None:
        st.warning(view.unavailable_reason or "No frame read.")
        return

    st.write(f"**Detected:** {'Yes' if view.detected else 'No'}")
    st.write(f"**Face count:** {view.face_count}")
    st.write(f"**Confidence:** {view.confidence if view.confidence is not None else 'N/A (detector does not provide one)'}")
    st.caption(f"Timestamp: {view.timestamp}")


def render_interaction_panel(service: DashboardService) -> None:
    st.markdown("##### Interaction")
    language_choice = st.selectbox("Language hint", ["Auto-detect", "English", "Arabic"], key="lang_choice")
    lang = {"English": Language.ENGLISH, "Arabic": Language.ARABIC}.get(language_choice)

    text = st.text_input("Student utterance (demo input — no microphone required)", key="utterance_input")
    if st.button("Send", key="send_utterance") and text.strip():
        st.session_state["interaction_view"] = service.handle_utterance(text, language=lang)

    if st.button("Reset conversation", key="reset_conversation"):
        service.reset_conversation()
        st.session_state.pop("interaction_view", None)

    view = st.session_state.get("interaction_view")
    if view is None:
        st.info("No interaction yet this session.")
        return

    st.write(f"**You:** {view.user_text}")
    st.write(f"**Response:** {view.spoken_text}")
    st.caption(
        f"type={view.response_type} | language={view.language} | "
        f"intent={view.intent_label or 'n/a'} "
        f"({view.intent_confidence:.2f})" if view.intent_confidence is not None else
        f"type={view.response_type} | language={view.language} | intent={view.intent_label or 'n/a'}"
    )
    if view.requires_clarification:
        st.caption("System is waiting on clarification.")


def render_navigation_panel(service: DashboardService) -> None:
    st.markdown("#### Navigation")
    cols = st.columns([2, 2, 1])
    origin = cols[0].text_input("Origin", value="Entrance", key="nav_origin")
    destination = cols[1].text_input("Destination", value="AI Lab", key="nav_destination")
    if cols[2].button("Find route", key="find_route"):
        st.session_state["nav_view"] = service.request_route(origin, destination)

    view = st.session_state.get("nav_view")
    if view is None:
        st.info("No route requested yet this session.")
        return

    if view.route is None:
        st.warning(view.message or "Route unavailable.")
        return

    route = view.route
    st.write(f"**Destination:** {route.destination_name}")
    if route.total_distance_meters is not None:
        st.write(f"**Total distance:** {route.total_distance_meters}")
    for step in route.steps:
        st.write(f"{step.index}. {step.instruction}" + (f" ({step.distance_meters})" if step.distance_meters else ""))
    if view.message:
        st.caption(view.message)


def render_robot_panel(service: DashboardService) -> None:
    st.markdown("#### Robot")
    st.caption("DEMO / SIMULATION MODE — running on the project's SimulatedRobotBackend, no physical hardware required.")

    action_cols = st.columns(4)
    actions = [
        ("Greet", "GREET"),
        ("Wave", "WAVE"),
        ("Idle", "IDLE"),
        ("Stop", "STOP"),
    ]
    for col, (label, key) in zip(action_cols, actions):
        if col.button(label, key=f"robot_{key}"):
            st.session_state["robot_view"] = service.robot_action(key)

    speak_text = st.text_input("Text for Speak / Explain actions", value="Welcome to the AI University Lab.", key="robot_speak_text")
    explain_cols = st.columns(5)
    explain_actions = [
        ("Speak", "SPEAK"),
        ("Explain AI", "EXPLAIN_AI"),
        ("Explain Robotics", "EXPLAIN_ROBOTICS"),
        ("Explain Training", "EXPLAIN_TRAINING"),
        ("Explain Lab", "EXPLAIN_LAB"),
    ]
    for col, (label, key) in zip(explain_cols, explain_actions):
        if col.button(label, key=f"robot_{key}"):
            st.session_state["robot_view"] = service.robot_action(key, speak_text)

    view = st.session_state.get("robot_view")
    if view is None:
        st.info("No robot action triggered yet this session.")
        return

    st.write(f"**Backend:** {view.backend_mode}")
    st.write(f"**Last command:** {view.last_command}")
    st.write(f"**Result:** {'Success' if view.last_success else 'Failed'} — {view.last_message}")


def render_event_timeline(service: DashboardService) -> None:
    st.markdown("#### Event / Decision Timeline")
    events = service.session.events[-25:]
    if not events:
        st.info("No events yet this session. Timeline populates as you interact with the dashboard.")
        return
    for event in reversed(events):
        st.write(f"`{event.timestamp.strftime('%H:%M:%S')}`  **{event.source}**  {event.event}  —  {event.detail}")


def render_system_health(service: DashboardService) -> None:
    st.markdown("#### System Health")
    for card in service.system_health():
        st.write(f"{_STATE_COLOR.get(card.state, '⚪')} **{card.name}** — {card.state.value}: {card.detail}")


def render_demo_scenarios(service: DashboardService) -> None:
    st.markdown("#### Demo Scenarios")
    for scenario in service.demo_scenarios():
        cols = st.columns([3, 1])
        with cols[0]:
            st.write(f"**{scenario.title}** — {scenario.description}")
            if not scenario.available:
                st.caption(f"Unavailable — {scenario.unavailable_reason}")
        with cols[1]:
            if scenario.available and st.button("Run", key=f"scenario_{scenario.key}"):
                log = service.run_demo_scenario(scenario.key)
                st.session_state[f"scenario_log_{scenario.key}"] = log
        log = st.session_state.get(f"scenario_log_{scenario.key}")
        if log:
            for line in log:
                st.caption(line)


def main() -> None:
    service = get_service()

    render_header(service)
    st.divider()
    render_status_cards(service)
    st.divider()

    left, right = st.columns(2)
    with left:
        render_perception_panel(service)
    with right:
        render_interaction_panel(service)
    st.divider()

    render_navigation_panel(service)
    st.divider()

    render_robot_panel(service)
    st.divider()

    render_event_timeline(service)
    st.divider()

    tab_health, tab_demo = st.tabs(["System Health", "Demo Scenarios"])
    with tab_health:
        render_system_health(service)
    with tab_demo:
        render_demo_scenarios(service)


if __name__ == "__main__":
    main()
