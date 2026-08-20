"""
Tests for docs/interaction_scenarios.md.

This is a documentation-validation test, not a behavioral/integration
test: it parses the specification file as text and checks its
structure (unique scenario IDs, required sections present, MVP
scenarios documented, no accidental references implying an executable
dependency on protected modules).

It does NOT import app.vision, app.robot, app.decision, app.guide,
app.ml, app.dl, app.navigation, or app.main -- the Interaction
Scenarios layer is documentation-only and must remain independently
reviewable without any of those modules existing or running.
"""

import re
from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parent.parent / "docs" / "interaction_scenarios.md"

EXPECTED_MVP_IDS = {
    "INT-01", "INT-02", "INT-03", "INT-04", "INT-05",
    "INT-08", "INT-09", "INT-10", "INT-12",
}
EXPECTED_NICE_TO_HAVE_IDS = {"INT-06", "INT-07", "INT-11"}
EXPECTED_ALL_CORE_IDS = EXPECTED_MVP_IDS | EXPECTED_NICE_TO_HAVE_IDS


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Expected {DOC_PATH} to exist"
    return DOC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def scenario_ids(doc_text: str):
    # Matches "### INT-01 — Name" style headers.
    return re.findall(r"^### (INT-\d+)", doc_text, flags=re.MULTILINE)


class TestDocumentExists:
    def test_interaction_scenarios_doc_exists(self):
        assert DOC_PATH.exists()

    def test_document_is_not_empty(self, doc_text):
        assert len(doc_text.strip()) > 0

    def test_document_declares_specification_status(self, doc_text):
        assert "Specification / Acceptance Criteria" in doc_text
        assert "not implemented" in doc_text.lower()


class TestScenarioIdsAreUnique:
    def test_at_least_twelve_core_scenarios_documented(self, scenario_ids):
        assert len(scenario_ids) >= 12

    def test_scenario_ids_are_unique(self, scenario_ids):
        assert len(scenario_ids) == len(set(scenario_ids))

    def test_all_expected_core_scenarios_present(self, scenario_ids):
        assert EXPECTED_ALL_CORE_IDS <= set(scenario_ids)

    def test_scenario_ids_follow_naming_convention(self, scenario_ids):
        for scenario_id in scenario_ids:
            assert re.fullmatch(r"INT-\d{2}", scenario_id)


class TestRequiredSectionsExist:
    REQUIRED_HEADINGS = [
        "## 1. Purpose",
        "## 2. System actors",
        "## 3. Scenario format",
        "## 4. Core scenarios",
        "## 5. Combined requests",
        "## 6. Context-aware follow-up",
        "## 7. Error and fallback scenarios",
        "## 8. Multilingual scenarios",
        "## 9. Scenario state / lifecycle",
        "## 10. Responsibility matrix",
        "## 11. Integration contract guidance",
        "## 12. Acceptance criteria",
        "## 13. Traceability matrix",
        "## 14. MVP vs. Nice-to-have",
        "## 15. Future extensibility",
    ]

    @pytest.mark.parametrize("heading", REQUIRED_HEADINGS)
    def test_required_heading_present(self, doc_text, heading):
        assert heading in doc_text

    def test_scenario_schema_fields_documented(self, doc_text):
        required_fields = [
            "Scenario ID", "Name", "Priority", "Actor", "Preconditions",
            "Student Input", "Expected Perception", "Expected ML Result",
            "Expected Decision", "Guide Requirement", "Navigation Requirement",
            "Robot Speech", "Robot Gesture", "UI / Route Display",
            "Expected Outcome", "Failure / Fallback", "Integration Notes",
        ]
        for field in required_fields:
            assert field in doc_text, f"Missing scenario schema field: {field}"


class TestMvpScenariosPresent:
    def test_all_mvp_scenarios_documented(self, scenario_ids):
        assert EXPECTED_MVP_IDS <= set(scenario_ids)

    def test_mvp_section_lists_nine_scenarios(self, doc_text):
        # Section 14 explicitly states the MVP count -- pin it so the
        # document and this test can't silently drift apart.
        assert "9 scenarios" in doc_text

    def test_nice_to_have_section_lists_three_scenarios(self, doc_text):
        assert "3 scenarios" in doc_text


class TestNoForbiddenModuleDependencies:
    """
    The specification must never claim this document imports, calls,
    or requires any protected module to function as documentation --
    it should only *reference* their existing contracts by name.
    """

    def test_no_python_import_statements_in_the_document(self, doc_text):
        assert not re.search(r"^\s*(import|from)\s+app\.", doc_text, flags=re.MULTILINE)

    def test_test_module_itself_does_not_import_protected_modules(self):
        # Per Rule 11, only app.vision/app.robot/app.ml/app.dl/
        # app.navigation/app.main are forbidden for this layer.
        # app.decision and app.guide are explicitly NOT forbidden --
        # they're already-integrated, non-Person-1 modules, and the
        # accuracy checks below legitimately reference their existing,
        # frozen enums (read-only) to keep this document honest.
        import ast

        tree = ast.parse(open(__file__).read())
        mods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            elif isinstance(node, ast.Import):
                mods.extend(a.name for a in node.names)
        forbidden_prefixes = (
            "app.vision", "app.robot", "app.ml", "app.dl",
            "app.navigation", "app.main",
        )
        for mod in mods:
            assert not mod.startswith(forbidden_prefixes)


class TestExistingContractsReferencedAccurately:
    """
    Spot-checks that the document's references to existing contracts
    match what those contracts actually contain today, so the
    specification doesn't silently drift from reality.

    IMPORTANT: per Rule 11, this test file must NOT import app.robot,
    app.vision, app.ml, app.dl, app.navigation, or app.main. Only
    app.decision and app.guide are permitted (neither is in the
    forbidden list -- both are already-integrated, non-Person-1
    modules). The Robot command vocabulary is therefore checked
    against a hardcoded literal mirroring the frozen, documented list
    in docs/integration_contract.md, not by importing app.robot.
    """

    # Mirrors the exact, frozen vocabulary documented in
    # docs/integration_contract.md's "Robot command vocabulary"
    # section. Deliberately duplicated here (not imported from
    # app.robot) to respect Rule 11.
    _KNOWN_ROBOT_COMMAND_VALUES = {
        "GREET", "WAVE", "SPEAK", "EXPLAIN_AI", "EXPLAIN_ROBOTICS",
        "EXPLAIN_TRAINING", "EXPLAIN_LAB", "IDLE", "STOP",
    }

    def test_referenced_robot_commands_actually_exist(self, doc_text):
        referenced = set(re.findall(r"RobotCommandType\.([A-Z_]+)", doc_text))
        assert referenced <= self._KNOWN_ROBOT_COMMAND_VALUES

    def test_referenced_decision_event_types_actually_exist(self, doc_text):
        # Excludes the "Future Contract Proposal" section, which
        # explicitly and intentionally references a NOT-IMPLEMENTED,
        # hypothetical event type as a proposal -- that is the point
        # of that section, not a documentation error.
        future_proposal_start = doc_text.find("### Future Contract Proposal")
        acceptance_criteria_start = doc_text.find("## 12. Acceptance criteria")
        scoped_text = doc_text[:future_proposal_start] + doc_text[acceptance_criteria_start:]

        from app.decision.event_manager import DecisionEventType

        existing_values = {member.value for member in DecisionEventType}
        referenced = set(re.findall(r"DecisionEventType\.([A-Z_]+)", scoped_text))
        assert referenced <= existing_values

    def test_future_proposal_explicitly_marked_not_implemented(self, doc_text):
        # The one hypothetical DecisionEventType reference must live
        # inside a section explicitly marked as a non-implemented
        # proposal -- pinning that it's labeled correctly rather than
        # silently exempting it.
        section = doc_text[doc_text.find("### Future Contract Proposal"):]
        assert "NOT IMPLEMENTED" in section
        assert "INFORMATION_REQUESTED" in section

    def test_referenced_application_states_actually_exist(self, doc_text):
        from app.decision.event_manager import ApplicationState

        existing_values = {member.value for member in ApplicationState}
        referenced = set(re.findall(r"ApplicationState\.([A-Z_]+)", doc_text))
        assert referenced <= existing_values

    def test_referenced_locations_actually_exist_in_guide(self, doc_text):
        from app.guide.locations import LOCATION_CONTENT

        for location_id in ("ai_lab", "library"):
            assert location_id in LOCATION_CONTENT
            assert f'"{location_id}"' in doc_text
