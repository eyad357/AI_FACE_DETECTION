"""
Tests for the deterministic, presentation-only campus map/navigator
(app.ui.campus_map) and its wiring into app.ui.demo's "University
Assistant" dashboard.

Fully deterministic: no camera, no browser hardware, no network, and
no real NavigationService/pathfinding involved -- this widget is
intentionally a separate, static, hard-coded five-location map (see
the module docstring in app/ui/campus_map.py for why).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ui import campus_map


class TestResolveDestination:
    @pytest.mark.parametrize(
        "utterance,expected_id",
        [
            ("Where is the AI Lab?", "ai_lab"),
            ("How do I get to the AI Lab?", "ai_lab"),
            ("Where is the Robotics Lab?", "robotics_lab"),
            ("Show me the Robotics Lab.", "robotics_lab"),
            ("Where is the Library?", "library"),
            ("Take me to the Library.", "library"),
            ("Where is the Teaching Assistant Office?", "ta_office"),
            ("Where can I find the teaching assistant?", "ta_office"),
            ("Where is the Cafeteria?", "cafeteria"),
            ("I need the cafeteria.", "cafeteria"),
        ],
    )
    def test_recognized_phrasings_resolve_to_the_right_destination(self, utterance, expected_id):
        assert campus_map.resolve_destination(utterance) == expected_id

    def test_longer_more_specific_keyword_wins_over_a_shorter_one(self):
        # "ta office" and "teaching assistant office" could both match;
        # the longer, more specific keyword must win deterministically.
        assert campus_map.resolve_destination("teaching assistant office please") == "ta_office"

    def test_unknown_phrase_resolves_to_none(self):
        assert campus_map.resolve_destination("where is the moon") is None

    def test_empty_and_blank_input_resolves_to_none(self):
        assert campus_map.resolve_destination("") is None
        assert campus_map.resolve_destination("   ") is None


class TestMapData:
    def test_exactly_five_fixed_destinations(self):
        ids = [d.id for d in campus_map.all_destinations()]
        assert len(ids) == 5
        assert len(set(ids)) == 5

    def test_destination_labels_match_the_required_english_names(self):
        labels = {d.label for d in campus_map.all_destinations()}
        assert labels == {
            "AI Lab",
            "Robotics Lab",
            "Library",
            "Teaching Assistant Office",
            "Cafeteria",
        }

    def test_every_destination_has_a_hardcoded_instruction(self):
        for dest in campus_map.all_destinations():
            assert dest.instruction

    def test_get_destination_by_id_round_trips(self):
        for dest in campus_map.all_destinations():
            assert campus_map.get_destination(dest.id) is dest

    def test_get_destination_unknown_id_returns_none(self):
        assert campus_map.get_destination("moon_base") is None


class TestMapSvgRendering:
    def test_render_is_deterministic(self):
        assert campus_map.render_map_svg("ai_lab") == campus_map.render_map_svg("ai_lab")

    def test_render_contains_all_location_labels(self):
        svg = campus_map.render_map_svg(None)
        # Long labels may wrap across two <text> lines, so check per word.
        for dest in campus_map.all_destinations():
            for word in dest.label.split(" "):
                assert word in svg

    def test_render_contains_you_are_here_marker(self):
        svg = campus_map.render_map_svg(None)
        assert campus_map.ORIGIN_LABEL in svg

    def test_render_is_a_single_svg_element(self):
        svg = campus_map.render_map_svg(None)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_selecting_a_destination_changes_the_output(self):
        assert campus_map.render_map_svg(None) != campus_map.render_map_svg("cafeteria")

    def test_unknown_selection_id_does_not_crash_and_highlights_nothing(self):
        svg = campus_map.render_map_svg("not_a_real_place")
        assert svg == campus_map.render_map_svg(None)


class TestCampusNavigatorUi:
    """Streamlit AppTest coverage -- no browser, no camera hardware."""

    def _app(self):
        from streamlit.testing.v1 import AppTest

        repo_root = Path(__file__).resolve().parents[2]
        at = AppTest.from_file(str(repo_root / "app" / "ui" / "demo.py"), default_timeout=30)
        at.session_state["demo_stage"] = "assistant"
        at.run()
        return at

    def test_dashboard_shows_university_assistant_header(self):
        at = self._app()
        assert not at.exception
        body = "\n".join(md.value for md in at.markdown)
        assert "University Assistant" in body
        assert "How can I help you?" in body

    @pytest.mark.parametrize("dest_id", [d.id for d in campus_map.all_destinations()])
    def test_clicking_each_destination_button_selects_it(self, dest_id):
        at = self._app()
        at.button(key=f"campus_btn_{dest_id}").click().run()
        assert not at.exception
        assert at.session_state["campus_destination"] == dest_id

    def test_route_text_matches_the_selected_destination(self):
        at = self._app()
        at.button(key="campus_btn_library").click().run()
        assert not at.exception
        body = "\n".join(md.value for md in at.markdown)
        assert campus_map.get_destination("library").instruction in body

    def test_asking_about_a_known_place_selects_it(self):
        at = self._app()
        at.text_input(key="campus_query").set_value("Where is the cafeteria?").run()
        at.button(key="campus_ask").click().run()
        assert not at.exception
        assert at.session_state["campus_destination"] == "cafeteria"

    def test_unknown_place_shows_the_supported_locations_message(self):
        at = self._app()
        at.text_input(key="campus_query").set_value("where is the moon").run()
        at.button(key="campus_ask").click().run()
        assert not at.exception
        assert at.session_state["campus_unknown"] is True
        body = "\n".join(w.value for w in at.warning) if at.warning else ""
        assert campus_map.UNKNOWN_DESTINATION_MESSAGE in body
