# PHASE_REPORT — Interaction Scenarios

## 1. Phase name
Interaction Scenarios Specification (behavioral contract layer for the
AI University Assistant & Navigator Robot)

## 2. Objective
Define expected student-facing system behavior — greeting, information
requests, navigation requests, combined requests, help, multilingual
interaction, error/fallback handling, and session lifecycle — as a
documentation-first, implementation-independent specification, so
Person 1 (ML/DL/Navigation) and Person 2 (Robot/Guide) can build toward
the same precisely-specified behavior in parallel, ahead of a future
`app.main` integration phase.

## 3. Files added
- `docs/interaction_scenarios.md` — the full specification (17 sections, 12 core scenarios: `INT-01` through `INT-12`)
- `tests/test_interaction_scenarios.py` — 33 lightweight, documentation-validation tests

## 4. Files modified
**None.** This phase is purely additive — no existing file was changed.

## 5. Files protected and verified unchanged
`app/vision/`, `app/decision/`, `app/robot/`, `app/models/`, `app/ml/`,
`app/dl/`, `app/navigation/`, `app/config.py`, `app/main.py`, and (for
completeness, though not explicitly required to be frozen this phase)
`app/guide/` — all verified **byte-for-byte identical** before and
after, via `md5sum` diff across every file in each of those trees. All
8 pre-existing test files were also checksum-verified unmodified.

## 6. Tests before
201 passed, 2 skipped

## 7. Tests after
234 passed, 2 skipped (**33 new, 0 regressions, 0 existing tests modified**)

## 8. Scenario count
12 core scenarios (`INT-01` – `INT-12`), each fully specified against
the 17-field schema (Scenario ID, Name, Priority, Actor(s),
Preconditions, Student Input, Expected Perception, Expected ML Result,
Expected Decision, Guide Requirement, Navigation Requirement, Robot
Speech, Robot Gesture, UI / Route Display, Expected Outcome, Failure /
Fallback, Integration Notes).

## 9. MVP scenario count
9 — `INT-01` (Greeting), `INT-02` (Information), `INT-03`
(Navigation), `INT-04` (Combined), `INT-05` (Help), `INT-08` (English
baseline), `INT-09` (Unknown request), `INT-10` (Destination not
found), `INT-12` (Session completion).

## 10. Nice-to-have scenario count
3 — `INT-06` (Context-aware follow-up), `INT-07` (Arabic), `INT-11`
(Navigation completion as a distinct scenario).

## 11. Dependency analysis
- `docs/interaction_scenarios.md` contains **zero** Python import
  statements (verified by regex test) — it references existing
  contracts (`RobotCommandType`, `DecisionEventType`, `ApplicationState`,
  `GuideResponse`, `LOCATION_CONTENT`) by name only, as prose/tables.
- `tests/test_interaction_scenarios.py` imports only: Python stdlib
  (`re`, `pathlib`, `ast`), `pytest`, and — for two narrow,
  read-only accuracy spot-checks — `app.decision.event_manager` and
  `app.guide.locations`. **Neither is forbidden by Rule 11** (only
  `app.vision`, `app.robot`, `app.ml`, `app.dl`, `app.navigation`, and
  `app.main` are). The Robot command vocabulary is checked against a
  **hardcoded literal**, not an `app.robot` import, specifically to
  respect Rule 11's explicit prohibition on that one.
- AST-verified: zero references to `app.vision`, `app.robot`, `app.ml`,
  `app.dl`, `app.navigation`, or `app.main` anywhere in either new file.

## 12. Integration compatibility
The document explicitly separates what's **already implemented** (the
topic/`EXPLANATION_REQUIRED` flow, the greeting/cooldown flow, Guide's
location lookup) from what's **future work** (ML intent classification,
Navigation routing, the Decision/`app.main` extensions needed to wire
free-text requests through). One "Future Contract Proposal" section
identifies two possible future contract needs (a directional Robot
gesture, and a new `DecisionEventType` for free-text-resolved targets)
and explicitly marks both as **NOT IMPLEMENTED**, requiring separate
approval — consistent with how every other cross-module contract change
in this project has been handled (audit → propose → approve → implement).

## 13. Person 1 impact
**Zero.** `app/ml/`, `app/dl/`, `app/navigation/`, `app/vision/` were
not read for modification purposes beyond inspecting their existing
docstrings (to cite their already-documented planned contracts
accurately), and were not modified in any way.

## 14. Person 2 impact
**Zero code impact.** `app/robot/`, `app/guide/` were not modified. The
document references existing Robot commands and Guide's existing
`get_location_info()`/`LOCATION_CONTENT` by name for scenario grounding
only.

## 15. Known limitations
- The specification's "future" scenarios (`INT-02` through `INT-11`,
  except the already-implemented `INT-01`/`INT-12`) describe intended
  behavior but cannot be executed end-to-end — ML, Navigation, and the
  relevant Decision/`app.main` extensions don't exist yet.
- `INT-06` (context-aware follow-up) requires session/conversation
  memory, which has no analog anywhere in the current architecture; it
  is explicitly deferred (Nice-to-have) rather than designed in detail.
- `INT-07` (Arabic) requires bilingual content fields not yet added to
  `LOCATION_CONTENT`/`TOPIC_CONTENT`, and an ML model capable of
  Arabic classification — both future work.
- The accuracy-checking tests (`TestExistingContractsReferencedAccurately`)
  will need updating if `DecisionEventType`/`ApplicationState`/
  `LOCATION_CONTENT` genuinely change in a future, separately-approved
  phase — this is intentional (they're meant to catch drift, not
  freeze the referenced modules).

## 16. Future extension points
- Adding `INT-13`/`INT-14`/`INT-15` (Nearby Places, Recommendation,
  Accessibility) only requires a new row per the existing schema — no
  code change.
- The "Future Contract Proposal" section is the designated place to
  formally propose the two flagged future contract needs once ML/
  Navigation exist and a concrete need is confirmed.
- `tests/test_interaction_scenarios.py` can grow additional
  accuracy-checks as new contracts are introduced, without needing to
  import any currently-forbidden module.
