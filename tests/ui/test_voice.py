"""
Tests for the browser-only voice feedback feature in app.ui.demo
("University Assistant" dashboard + campus navigator).

Fully deterministic: no camera, no browser hardware, no microphone/
speaker/audio device, and no network -- the actual speaking happens
in the user's browser via window.speechSynthesis, which cannot (and
should not) be exercised from a headless test. These tests instead
verify the Python-side contract that decides *what* gets queued to
speak and *when*, per the "avoid repeated speech" requirement.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ui import campus_map


def _app(default_stage: str = "assistant"):
    from streamlit.testing.v1 import AppTest

    repo_root = Path(__file__).resolve().parents[2]
    at = AppTest.from_file(str(repo_root / "app" / "ui" / "demo.py"), default_timeout=30)
    at.session_state["demo_stage"] = default_stage
    at.run()
    return at


class TestNoBackendOrCloudDependencyWasIntroduced:
    """
    Requirement: browser-only Web Speech API, no LLM / external TTS /
    cloud speech service / API key of any kind.
    """

    def _demo_source(self) -> str:
        repo_root = Path(__file__).resolve().parents[2]
        return (repo_root / "app" / "ui" / "demo.py").read_text(encoding="utf-8")

    def test_uses_the_browser_web_speech_api(self):
        source = self._demo_source()
        assert "speechSynthesis" in source
        assert "SpeechSynthesisUtterance" in source
        assert 'lang = "en-US"' in source

    def test_no_cloud_or_llm_tts_provider_is_referenced(self):
        source = self._demo_source().lower()
        forbidden = (
            "openai",
            "elevenlabs",
            "azure",
            "google.cloud",
            "googletts",
            "polly",
            "pyttsx3",
            "api_key",
            "apikey",
        )
        for term in forbidden:
            assert term not in source, f"unexpected TTS/cloud dependency reference: {term!r}"

    def test_no_new_pip_dependency_was_added(self):
        repo_root = Path(__file__).resolve().parents[2]
        requirements = (repo_root / "requirements.txt").read_text(encoding="utf-8").lower()
        for term in ("openai", "elevenlabs", "azure", "google-cloud", "boto3", "pyttsx3"):
            assert term not in requirements


class TestDestinationSpeechText:
    def test_every_destination_has_nonempty_navigation_instruction(self):
        for dest in campus_map.all_destinations():
            assert isinstance(dest.instruction, str)
            assert dest.instruction.strip()

    def test_unknown_destination_message_is_nonempty(self):
        assert campus_map.UNKNOWN_DESTINATION_MESSAGE.strip()


class TestVoiceControlState:
    def test_voice_defaults_to_enabled(self):
        at = _app()
        assert not at.exception
        assert at.session_state["voice_enabled"] is True

    def test_toggle_button_disables_voice(self):
        at = _app()
        at.button(key="voice_toggle").click().run()
        assert not at.exception
        assert at.session_state["voice_enabled"] is False

    def test_toggle_button_twice_re_enables_voice(self):
        at = _app()
        at.button(key="voice_toggle").click().run()
        at.button(key="voice_toggle").click().run()
        assert not at.exception
        assert at.session_state["voice_enabled"] is True


class TestSpeechIsQueuedOnlyByUserActions:
    def test_picking_a_destination_queues_its_instruction(self):
        at = _app()
        at.button(key="campus_btn_library").click().run()
        assert not at.exception
        assert at.session_state["voice_last_text"] == campus_map.get_destination("library").instruction

    @pytest.mark.parametrize("dest_id", [d.id for d in campus_map.all_destinations()])
    def test_each_destination_button_queues_its_own_instruction(self, dest_id):
        at = _app()
        at.button(key=f"campus_btn_{dest_id}").click().run()
        assert not at.exception
        assert at.session_state["voice_last_text"] == campus_map.get_destination(dest_id).instruction

    def test_asking_about_an_unknown_place_queues_the_supported_locations_message(self):
        at = _app()
        at.text_input(key="campus_query").set_value("where is the moon").run()
        at.button(key="campus_ask").click().run()
        assert not at.exception
        assert at.session_state["voice_last_text"] == campus_map.UNKNOWN_DESTINATION_MESSAGE

    def test_asking_about_ai_queues_the_guide_answer(self):
        at = _app()
        at.button(key="demo_btn_ASK_AI").click().run()
        assert not at.exception
        result = at.session_state["demo_result"]
        assert at.session_state["voice_last_text"] == result["text"]

    def test_find_a_lab_queues_the_navigation_spoken_text(self):
        at = _app()
        at.button(key="demo_btn_nav").click().run()
        assert not at.exception
        result = at.session_state["demo_result"]
        assert at.session_state["voice_last_text"] == result["spoken_text"]

    def test_arabic_demo_does_not_queue_speech(self):
        # Browser voice is English-only; Arabic turns must not be queued.
        at = _app()
        at.button(key="demo_btn_arabic").click().run()
        assert not at.exception
        assert "voice_pending_text" not in at.session_state
        assert "voice_last_text" not in at.session_state

    def test_pending_speech_is_not_replayed_on_an_unrelated_rerun(self):
        # The "avoid repeated speech" requirement: after the run that
        # queued speech is followed by an unrelated widget interaction,
        # nothing should still be pending.
        at = _app()
        at.button(key="campus_btn_cafeteria").click().run()
        assert "voice_pending_text" not in at.session_state  # consumed by render_voice_script()

        # A second, unrelated interaction must not resurrect it.
        at.text_input(key="campus_query").set_value("just typing, not asking").run()
        assert "voice_pending_text" not in at.session_state
        # The last-spoken text is still remembered for Repeat, though.
        assert at.session_state["voice_last_text"] == campus_map.get_destination("cafeteria").instruction

    def test_voice_disabled_still_records_last_text_but_does_not_render_speech(self):
        at = _app()
        at.button(key="voice_toggle").click().run()  # turn voice off
        at.button(key="campus_btn_ai_lab").click().run()
        assert not at.exception
        assert at.session_state["voice_enabled"] is False
        assert at.session_state["voice_last_text"] == campus_map.get_destination("ai_lab").instruction


class TestRepeatUsesTheCurrentInstruction:
    def test_repeat_requeues_the_last_spoken_instruction(self):
        at = _app()
        at.button(key="campus_btn_robotics_lab").click().run()
        assert "voice_pending_text" not in at.session_state  # already consumed this run

        at.button(key="voice_repeat").click().run()
        assert not at.exception
        expected = campus_map.get_destination("robotics_lab").instruction
        # Consumed again by this run's render_voice_script(), but the
        # remembered last-spoken text still matches what Repeat replayed.
        assert at.session_state["voice_last_text"] == expected

    def test_repeat_with_nothing_spoken_yet_does_not_error(self):
        at = _app()
        at.button(key="voice_repeat").click().run()
        assert not at.exception
        assert "voice_pending_text" not in at.session_state
