# Interaction Scenarios

**Status:** Specification / Acceptance Criteria — **not implemented**.

This document defines *expected system behavior*, independent of
implementation. It is a behavioral contract, not code: nothing in this
file (or its companion test) imports, calls, or modifies any of Vision,
ML, DL, Decision, Guide, Navigation, Robot, or `app.main`. It exists so
Person 1 (ML/DL/Navigation) and Person 2 (Robot/Guide) can build toward
the same, precisely-specified end-to-end behavior in parallel, and so a
future integration phase (in `app.main`, and only there) has a single
source of truth for what "done" looks like.

Every contract referenced below (`RobotCommandType`, `GuideTopic`,
`DecisionEventType`, `ApplicationState`, `GuideResponse`,
`LOCATION_CONTENT`) already exists in the repository today and is used
exactly as-is — no new contract is created by this document except
where explicitly marked **"Future Contract Proposal — NOT IMPLEMENTED."**

---

## 1. Purpose

Interaction Scenarios exist to answer *"what should the system do,
from the student's point of view?"* — separately from *"how is it
built?"* This lets:

- Person 1 implement ML/DL/Navigation against a fixed, documented
  input/output shape, without needing Person 2's Robot/Guide code to
  exist or run.
- Person 2 implement Robot/Guide against the same fixed shape, without
  needing Person 1's ML/DL/Navigation code to exist or run.
- A future integration phase (`app.main`, per the existing
  architecture) wire the two together with a checklist of scenarios
  that must work, rather than an ambiguous verbal description.

This mirrors how the project's other specification-first phases have
worked (e.g. Guide's location data model was designed and approved
*before* implementation) — scenarios are the same idea applied to the
full student-facing experience.

## 2. System actors

| Actor | Responsibility | Owns |
|---|---|---|
| **Student** | Initiates interaction; asks questions in English or Arabic | — |
| **Vision** | "What do I see?" — detects a person is present | `app.vision` (implemented, frozen) |
| **DL** | "What gesture is being made?" — future gesture recognition | `app.dl` (scaffolded) |
| **ML** | "What does the student want?" — classifies free text into an intent | `app.ml` (scaffolded) |
| **Decision** | "What should happen next?" — the application state machine | `app.decision` (implemented, frozen) |
| **Guide** | "What information should be given?" — location/topic content | `app.guide` (implemented) |
| **Navigation** | "What is the route?" — pathfinding between locations | `app.navigation` (scaffolded) |
| **Robot** | "How is it physically done?" — executes commands | `app.robot` (implemented, frozen) |
| **main.py** | "How are all of the above wired together?" — the *only* orchestrator | `app.main` |

This document does **not** own or modify any of the above. It only
describes the expected interplay between them.

## 3. Scenario format

Every scenario in Section 4 follows this schema:

| Field | Meaning |
|---|---|
| **Scenario ID** | Stable identifier, e.g. `INT-01` |
| **Name** | Short human-readable name |
| **Priority** | `MVP` or `Nice-to-have` (see Section 14) |
| **Actor(s)** | Which system actors participate (Section 2) |
| **Preconditions** | System state required before the scenario begins |
| **Student Input** | What the student says or does (realistic example) |
| **Expected Perception** | What Vision/DL are expected to report |
| **Expected ML Result** | The expected intent classification (future contract) |
| **Expected Decision** | The expected Decision-layer behavior, in terms of existing or future `DecisionEventType`/`ApplicationState` values |
| **Guide Requirement** | What Guide is expected to be asked for / return |
| **Navigation Requirement** | What Navigation is expected to be asked for / return |
| **Robot Speech** | What the robot should say, and via which existing `RobotCommandType` |
| **Robot Gesture** | Which existing `RobotCommandType` (if any) expresses this physically |
| **UI / Route Display** | What should be shown on-screen, if applicable |
| **Expected Outcome** | Plain-language description of success |
| **Failure / Fallback** | What happens if something goes wrong |
| **Integration Notes** | Pointers to the existing contracts/files a future integration phase would touch |

This schema is deliberately implementation-independent: it names
*existing enum values and result-type concepts*, never function calls,
file paths to modify, or internal state variables.

## 4. Core scenarios

> All locations referenced below (AI Lab, Library, Engineering
> Building, Student Affairs, etc.) are the existing **prototype**
> entries already in `app.guide.locations.LOCATION_CONTENT` — see
> that module's own disclaimer. They do not describe any real
> university.

### INT-01 — Automatic Greeting

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | Vision, Decision, Robot |
| Preconditions | `ApplicationState.WAITING`; no visitor currently detected |
| Student Input | Student walks into the robot's field of view (no speech yet) |
| Expected Perception | Vision reports a stable `DetectionResult` (`detected=True`, `face_count>=1`) for `CONFIG.vision.detection_frames_required` consecutive frames — exactly the existing stability rule in `app.decision.state_manager` |
| Expected ML Result | Not applicable — no question has been asked yet |
| Expected Decision | Existing `DecisionEventType.GREETING_REQUIRED`; state moves `WAITING → GREETING` (both already implemented, unchanged) |
| Guide Requirement | None |
| Navigation Requirement | None |
| Robot Speech | None required (greeting may be gesture-only) |
| Robot Gesture | Existing `RobotCommandType.GREET` |
| UI / Route Display | Optional: "Hello! How can I help you?" |
| Expected Outcome | The robot visibly acknowledges the student within the existing stability window |
| Failure / Fallback | Flickery detection must not cause repeated greetings — already guaranteed by the existing stability + cooldown logic |
| Integration Notes | Already fully implemented end-to-end (Phase 7): `StateManager.process()` → `GREETING_REQUIRED` → `app.main` → `RobotCommand(GREET)`. This scenario documents existing, working behavior. |

### INT-02 — Information Request

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | ML, Decision, Guide, Robot |
| Preconditions | A greeting has occurred (or the student speaks directly) |
| Student Input | *"What can I do in the AI Lab?"* |
| Expected Perception | N/A (text input) |
| Expected ML Result | *(Future contract)* `IntentResult(intent=INFORMATION, target="ai_lab")` |
| Expected Decision | *(Future)* a Decision event carrying the resolved information request — see Section 11 |
| Guide Requirement | `GuideService.get_location_info("ai_lab")` — **already implemented** (Guide G1), returns a `GuideResponse` with `spoken_text` |
| Navigation Requirement | None |
| Robot Speech | The `GuideResponse.spoken_text`, delivered via existing `RobotCommandType.SPEAK` |
| Robot Gesture | None required |
| UI / Route Display | Optional: display `GuideResponse.title` / `summary` |
| Expected Outcome | Student receives accurate, existing prototype information about the AI Lab |
| Failure / Fallback | Unknown location → Guide's existing "Location Unavailable" controlled response (already implemented and tested); robot says it doesn't have that information rather than inventing content |
| Integration Notes | Guide side is fully ready today. ML side and the Decision→Guide wiring for *free-text* information requests are future work (Section 11). |

### INT-03 — Navigation Request

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | ML, Decision, Navigation, Robot |
| Preconditions | A greeting has occurred (or the student speaks directly) |
| Student Input | *"Where is the library?"* |
| Expected Perception | N/A |
| Expected ML Result | *(Future)* `IntentResult(intent=NAVIGATION, target="library")` |
| Expected Decision | *(Future)* a Decision event carrying the resolved navigation request |
| Guide Requirement | None (Guide does not calculate routes — see Section 5) |
| Navigation Requirement | *(Future)* `NavigationService.find_route(RouteRequest(destination="library"))` → `RouteResult` |
| Robot Speech | A route summary derived from `RouteResult`, via existing `RobotCommandType.SPEAK` |
| Robot Gesture | Optional directional gesture — no dedicated `RobotCommandType` exists for this today; see Section 11's Future Contract Proposal note |
| UI / Route Display | Route/path display, if a UI exists |
| Expected Outcome | Student receives route guidance to the library |
| Failure / Fallback | See INT-10 (Destination Not Found) |
| Integration Notes | Requires `app.navigation`'s first real implementation (currently scaffolded only) plus ML and a Decision/`app.main` extension — none of which exist yet. |

### INT-04 — Combined Information + Navigation Request

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | ML, Decision, Guide, Navigation, Robot |
| Preconditions | A greeting has occurred (or the student speaks directly) |
| Student Input | *"Where is the AI Lab and what can I do there?"* |
| Expected Perception | N/A |
| Expected ML Result | *(Future)* `IntentResult(intent=COMBINED, target="ai_lab")` |
| Expected Decision | *(Future)* a Decision event that fans out to both Guide and Navigation requests for the same target |
| Guide Requirement | `GuideService.get_location_info("ai_lab")` — already implemented |
| Navigation Requirement | *(Future)* `NavigationService.find_route(...)` for the same target |
| Robot Speech | A composed response using both `GuideResponse.spoken_text` and the route summary, via existing `RobotCommandType.SPEAK` |
| Robot Gesture | None required |
| UI / Route Display | Both information and route, if a UI exists |
| Expected Outcome | Student receives both pieces of information in one exchange |
| Failure / Fallback | If Navigation fails but Guide succeeds (or vice versa), the robot should still deliver the half that succeeded rather than failing the whole request — see Section 7 |
| Integration Notes | See Section 5 for the full conceptual flow diagram. Guide's contribution here is already implemented; the fan-out/compose step is future `app.main` work. |

### INT-05 — "I'm Lost" Assistance

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | ML, Decision, Robot |
| Preconditions | Student is near the robot |
| Student Input | *"I'm lost, can you help me?"* |
| Expected Perception | N/A |
| Expected ML Result | *(Future)* `IntentResult(intent=HELP)` |
| Expected Decision | *(Future)* a Decision event routing to a help/assistance response |
| Guide Requirement | None (no specific destination yet — see INT-06 for the natural follow-up) |
| Navigation Requirement | None |
| Robot Speech | A general offer of help, e.g. *"I can help. Which place are you looking for?"*, via `RobotCommandType.SPEAK` |
| Robot Gesture | Existing `RobotCommandType.WAVE` (friendly acknowledgment) |
| UI / Route Display | Optional prompt for a destination |
| Expected Outcome | Student is invited to name a destination, transitioning naturally into INT-02/INT-03/INT-04 |
| Failure / Fallback | If the student doesn't name a destination, the robot should not repeat the same prompt indefinitely — a bounded retry/timeout, deferred to a future Decision extension |
| Integration Notes | `HELP` is already a planned ML intent (see `app.ml`'s own docstring). No Decision/main.py wiring exists yet. |

### INT-06 — Context-aware Follow-up

| Field | Value |
|---|---|
| Priority | Nice-to-have |
| Actor(s) | ML, Decision, Guide |
| Preconditions | A destination was already resolved earlier in the same session (e.g. via INT-03) |
| Student Input | Turn 1: *"Where is the AI Lab?"* → Turn 2: *"What can I do there?"* |
| Expected Perception | N/A |
| Expected ML Result | *(Future)* Turn 2's `IntentResult(intent=INFORMATION, target=None)` — "there" is not a location name ML can resolve alone |
| Expected Decision | *(Future)* Decision resolves "there" to the most recently mentioned target from Turn 1 (`"ai_lab"`) |
| Guide Requirement | `GuideService.get_location_info("ai_lab")` — same call as INT-02, once the target is resolved |
| Navigation Requirement | None |
| Robot Speech | Information about the AI Lab, via `RobotCommandType.SPEAK` |
| Robot Gesture | None required |
| UI / Route Display | Optional |
| Expected Outcome | The student does not have to repeat the location name |
| Failure / Fallback | If no prior destination exists in the session, treat as INT-09 (Unknown/Unsupported) rather than guessing |
| Integration Notes | Requires session/context memory, which does **not** exist anywhere in the current architecture. This is explicitly **not implemented** — see Section 15 (Nice-to-have). No existing module is modified by documenting this. |

### INT-07 — Arabic Interaction

| Field | Value |
|---|---|
| Priority | Nice-to-have |
| Actor(s) | ML, Decision, Guide, Robot |
| Preconditions | Same as INT-02/INT-03 |
| Student Input | *"فين معمل الذكاء الاصطناعي؟"* (*"Where is the AI Lab?"*) |
| Expected Perception | N/A |
| Expected ML Result | *(Future)* `IntentResult(intent=NAVIGATION, target="ai_lab")` — same result shape as English, language-agnostic at the contract level |
| Expected Decision | Same as INT-03 |
| Guide Requirement | Same as INT-03/INT-02, in Arabic — requires Arabic `spoken_text` content, not yet present in `LOCATION_CONTENT`/`TOPIC_CONTENT` (both are English-only today) |
| Navigation Requirement | Same as INT-03 |
| Robot Speech | Arabic response text, via existing `RobotCommandType.SPEAK` (the command itself is language-agnostic — it just carries `text: str`) |
| Robot Gesture | Same as INT-03 |
| UI / Route Display | Arabic-language display, if a UI exists |
| Expected Outcome | Same experience as INT-03, in Arabic |
| Failure / Fallback | If Arabic content is not yet available for a given location, fall back to a clear "not available in Arabic yet" message rather than silently answering in English |
| Integration Notes | No translation library is required or assumed — see `docs/guide.md`'s existing "Future Language Support" note. Requires bilingual content fields to be added to `LOCATION_CONTENT`/`TOPIC_CONTENT` (additive, no structural change) and an ML model trained/evaluated on Arabic input. **Not implemented.** |

### INT-08 — English Interaction

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | ML, Decision, Guide, Navigation, Robot |
| Preconditions | Same as INT-02/INT-03 |
| Student Input | Any of the English examples above |
| Expected Perception | N/A |
| Expected ML Result | Standard case — see INT-02/INT-03/INT-04 |
| Expected Decision | As per the matching scenario |
| Guide Requirement | As per the matching scenario |
| Navigation Requirement | As per the matching scenario |
| Robot Speech | English response text |
| Robot Gesture | As per the matching scenario |
| UI / Route Display | English display |
| Expected Outcome | Baseline, default-language experience |
| Failure / Fallback | As per the matching scenario |
| Integration Notes | This scenario exists mainly to make explicit that English is the default/baseline language this project already supports (all current `LOCATION_CONTENT`/`TOPIC_CONTENT` is English), before INT-07 layers Arabic on top. |

### INT-09 — Unknown / Unsupported Request

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | ML, Decision, Robot |
| Preconditions | Student has spoken |
| Student Input | *"Can you do my homework?"* / any out-of-scope request |
| Expected Perception | N/A |
| Expected ML Result | *(Future)* `IntentResult(intent=UNKNOWN)` — the planned ML intent set already includes `UNKNOWN` (see `app.ml`'s own docstring) for exactly this case, e.g. via a confidence threshold |
| Expected Decision | *(Future)* a Decision event routing to a polite "can't help with that" response |
| Guide Requirement | None |
| Navigation Requirement | None |
| Robot Speech | A polite, honest decline, e.g. *"I'm not able to help with that, but I can tell you about places on campus."*, via `RobotCommandType.SPEAK` |
| Robot Gesture | None required |
| UI / Route Display | Optional: suggest example questions |
| Expected Outcome | Student is not misled into thinking the robot attempted and failed — it clearly didn't understand |
| Failure / Fallback | This scenario **is** the fallback for out-of-scope input; it must never fabricate an answer |
| Integration Notes | Depends on ML's confidence-threshold behavior at inference time (documented in `app.ml`'s scaffold, not yet implemented). |

### INT-10 — Destination Not Found

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | ML, Decision, Navigation, Robot |
| Preconditions | Student asked a navigation-shaped question |
| Student Input | *"Where is the swimming pool?"* (not a prototype location) |
| Expected Perception | N/A |
| Expected ML Result | *(Future)* `IntentResult(intent=NAVIGATION, target=None)` or an unresolvable target string |
| Expected Decision | *(Future)* routes to a "destination not found" response rather than a Navigation call with no target |
| Guide Requirement | None |
| Navigation Requirement | *(Future)* `NavigationService.find_route(...)` returns a "not found"-shaped `RouteResult`, or is never called if the target didn't resolve |
| Robot Speech | *"I don't have information about that location."* — never a fabricated route, via `RobotCommandType.SPEAK` |
| Robot Gesture | None required |
| UI / Route Display | Optional: suggest known locations |
| Expected Outcome | Student is told clearly and honestly that the destination is unknown |
| Failure / Fallback | This scenario **is itself** the fallback for INT-03/INT-04 when the target doesn't resolve |
| Integration Notes | Guide already has this exact pattern implemented today — `GuideService.get_location_info("not_a_real_place")` returns a controlled "Location Unavailable" response rather than raising (see `tests/test_guide.py::TestUnknownLocationHandling`). Navigation should follow the same principle once implemented. |

### INT-11 — Navigation Completion

| Field | Value |
|---|---|
| Priority | Nice-to-have |
| Actor(s) | Robot, UI |
| Preconditions | A navigation response was already delivered (INT-03/INT-04) |
| Student Input | None — this is a system-driven follow-up, or an explicit *"thanks, I found it"* |
| Expected Perception | N/A |
| Expected ML Result | N/A |
| Expected Decision | *(Future)* returns toward `ApplicationState.WAITING`/`COOLDOWN`, mirroring the existing `SESSION_COMPLETED`/`COOLDOWN_STARTED` pattern already used for the topic-explanation flow |
| Guide Requirement | None |
| Navigation Requirement | None |
| Robot Speech | Optional closing remark, e.g. *"Let me know if you need anything else."*, via `RobotCommandType.SPEAK` |
| Robot Gesture | None required |
| UI / Route Display | Route display cleared |
| Expected Outcome | Clean session end, ready for the next visitor |
| Failure / Fallback | N/A |
| Integration Notes | Directly mirrors the existing, already-implemented `EXPLANATION_REQUIRED → SESSION_COMPLETED → COOLDOWN_STARTED (→ RobotCommand(IDLE))` pattern in `app.decision.state_manager` / `app.main`. No new state-machine concept is required — a future extension would reuse it for navigation sessions too. |

### INT-12 — Conversation / Session Completion

| Field | Value |
|---|---|
| Priority | MVP |
| Actor(s) | Decision, Robot |
| Preconditions | Any prior scenario has completed |
| Student Input | Student walks away, or says *"thank you, goodbye"* |
| Expected Perception | Vision stops reporting a stable detection (existing `visitor_lost_frames_required` logic) |
| Expected ML Result | N/A (or `IntentResult(intent=UNKNOWN)`/a future `GOODBYE`-style intent, out of scope for MVP) |
| Expected Decision | Existing `DecisionEventType.COOLDOWN_STARTED` → `RETURN_TO_WAITING`; state returns to `ApplicationState.WAITING` — **already fully implemented, unchanged** |
| Guide Requirement | None |
| Navigation Requirement | None |
| Robot Speech | None required |
| Robot Gesture | Existing `RobotCommandType.IDLE` |
| UI / Route Display | Cleared |
| Expected Outcome | Robot is ready for the next student without any lingering session state |
| Failure / Fallback | Already covered by the existing cooldown/visitor-lost stability logic — no flicker-triggered false resets |
| Integration Notes | Fully implemented today (Phase 2/7): `StateManager`'s `COOLDOWN → WAITING` transition, dispatched to `RobotCommandType.IDLE` by `app.main`. This scenario documents existing, working behavior. |

## 5. Combined requests — conceptual flow

```
Student Question
        |
        v
       ML                          <- future (app.ml)
        |
        v
    COMBINED
        |
        v
    Decision                       <- future extension of app.decision
      /     \
     v       v
  Guide   Navigation                <- Guide: implemented (G1) | Navigation: scaffolded
     \       /
      \     /
       v   v
     Response (composed)           <- future, in app.main
        |
        v
      Robot                        <- implemented, unchanged
```

This is a **future integration flow**. Nothing above is implemented in
this phase. Guide's box is the only one with real behavior behind it
today (`GuideService.get_location_info()`); every other box is either
scaffolded-only or does not exist yet.

## 6. Context-aware follow-up

See INT-06 in full above. Summary: this requires **session/conversation
memory**, which the current architecture has no concept of anywhere
(Decision's state machine tracks *application* state, not *dialogue*
history). This is explicitly a **Nice-to-have**, deferred, and its
inclusion here is a specification only — no memory mechanism is
implemented, proposed as code, or required by any other scenario.

## 7. Error and fallback scenarios

| Situation | Expected safe behavior | Existing precedent in this repo |
|---|---|---|
| Unknown location | Controlled "not available" response, never fabricated content | `GuideService.get_location_info()` — implemented |
| Unsupported question | `UNKNOWN` intent → polite decline (INT-09) | Planned in `app.ml`'s intent set |
| Missing destination | Ask for clarification once, don't loop indefinitely (INT-05) | New — future Decision behavior |
| Low-confidence intent | Treat as `UNKNOWN` rather than guessing | Planned in `app.ml`'s docstring ("UNKNOWN" intent exists for this) |
| Multiple possible destinations | Ask the student to disambiguate rather than picking arbitrarily | New — future Navigation/Decision behavior |
| Navigation unavailable | Still deliver Guide's half of a COMBINED request (INT-04) | New — future `app.main` composition logic |
| Guide information unavailable | Same pattern as "unknown location" above | Already implemented |
| Robot speech failure | `RobotExecutionResult.success=False`, logged, does not corrupt Decision state | Already implemented and tested (`tests/test_integration.py::TestRobotResultHandling::test_robot_failure_does_not_corrupt_decision_state`) |
| Student cancels request | Return to `WAITING`/`COOLDOWN` cleanly (INT-12) | Already implemented |

The unifying principle, already established by Guide's implementation
and carried forward here: **the robot must never invent university
information.** Every "not found"/"unavailable" case returns a
controlled, honest response.

## 8. Multilingual scenarios

See INT-07 (Arabic) and INT-08 (English) above for full detail. No
translation library is required or assumed by this specification —
Arabic support is planned as **parallel content fields** (e.g. an
Arabic `spoken_text` alongside the existing English one) plus an ML
model capable of classifying Arabic input, not as a runtime translation
step. Both are **future work**.

## 9. Scenario state / lifecycle

```
WAITING
   |
   v
DETECTED           <- Vision reports a stable visitor (existing)
   |
   v
GREETING           <- existing ApplicationState.GREETING
   |
   v
LISTENING          <- future: student is speaking / question is being captured
   |
   v
UNDERSTANDING      <- future: ML classifies intent
   |
   v
RESPONDING         <- Guide/Navigation are consulted, response composed
   |
   v
NAVIGATING / EXPLAINING   <- existing ApplicationState.EXPLAINING covers "EXPLAINING";
   |                          NAVIGATING is a future extension of the same idea
   v
COMPLETED          <- existing COOLDOWN_STARTED / SESSION_COMPLETED pattern
   |
   v
WAITING
```

**This is a behavioral description only.** The existing Decision state
machine (`ApplicationState`: `WAITING, GREETING, GUIDE_MENU, EXPLAINING,
COOLDOWN, ERROR`) is **not modified** by this document. `LISTENING`,
`UNDERSTANDING`, and `NAVIGATING` are conceptual/future states that a
later Decision extension *might* introduce — they do not exist in
`app.decision.event_manager.ApplicationState` today, and this document
does not add them.

## 10. Responsibility matrix

| Scenario responsibility | Module | Status |
|---|---|---|
| Person Detection | Vision | Implemented |
| Gesture Recognition | DL | Scaffolded |
| Question Classification | ML | Scaffolded |
| Intent → Action Decision | Decision | Implemented (topic flow) / Future (intent flow) |
| Location/Topic Information | Guide | Implemented |
| Route Calculation | Navigation | Scaffolded |
| Speech / Physical Action | Robot | Implemented |
| Orchestration | main.py | Implemented (topic flow) / Future (intent flow) |
| **Scenario specification itself** | **Interaction Scenarios (this document)** | **Specification / Acceptance Criteria — not an executable module** |

## 11. Integration contract guidance

Future modules should connect using **existing contract shapes** and
**existing patterns**, not new ones invented ad hoc:

- ML produces an `IntentResult` (not implemented yet; shape sketched in
  `app.ml`'s own docstring: intent ∈ {`INFORMATION`, `NAVIGATION`,
  `COMBINED`, `HELP`, `UNKNOWN`}).
- Navigation produces a `RouteResult` from a `RouteRequest` (not
  implemented yet; shape sketched in `app.navigation`'s own docstring).
- Guide produces `GuideResponse` — **already implemented**, reused
  as-is; no change needed for these scenarios.
- Robot receives the **existing** `RobotCommand`/`RobotCommandType` —
  no new command is required for any MVP scenario above; every MVP
  scenario routes through `GREET`, `WAVE`, `SPEAK`, or `IDLE`, all of
  which already exist.
- `app.main` orchestrates, following the exact same pattern already
  proven for the topic/`EXPLANATION_REQUIRED` flow
  (`DecisionEvent.metadata` carries the routing key; `app.main` looks
  it up and dispatches).

No new entry was added to `app/models/` to write this document, and
none is required by it.

### Future Contract Proposal — NOT IMPLEMENTED

Two future needs were identified while writing the scenarios above that
existing contracts don't yet cover. Both are proposals only:

1. **A directional/pointing gesture** for Navigation results (INT-03).
   No existing `RobotCommandType` represents "point in a direction."
   Proposal: reuse the existing `WAVE` for now (acknowledgment only,
   not directional), and revisit whether a new command is genuinely
   needed once real Navigation output exists to react to. **Do not add
   a new `RobotCommandType` speculatively** — this would violate Rule 6
   and is explicitly deferred.
2. **A Decision event carrying a free-text-resolved target** (e.g. for
   INT-02/INT-03/INT-04), analogous to the existing
   `EXPLANATION_REQUIRED` event but sourced from ML instead of a menu
   selection. Proposal shape (illustrative only):
   `DecisionEventType.INFORMATION_REQUESTED` /
   `NAVIGATION_REQUESTED(metadata={"target": location_id})`. **Not
   implemented; requires explicit approval and would modify
   `app/decision/event_manager.py`, a protected module.**

## 12. Acceptance criteria (Given/When/Then)

**INT-02 — Information Request**
> Given a student asks *"What can I do in the AI Lab?"*
> When the system classifies the request as `INFORMATION` and resolves
> the target to `"ai_lab"`,
> Then the system should retrieve information via `GuideService` and
> the robot should communicate it using the existing `SPEAK` command.

**INT-03 — Navigation Request**
> Given a student asks *"Where is the library?"*
> When the system classifies the request as `NAVIGATION` and resolves
> the target to `"library"`,
> Then the system should retrieve a route via the future Navigation
> service and the robot should communicate it using the existing
> `SPEAK` command.

**INT-04 — Combined Request**
> Given a student asks *"Where is the AI Lab and what can I do there?"*
> When the system classifies the request as `COMBINED` for target
> `"ai_lab"`,
> Then the system should retrieve both information (Guide) and a route
> (Navigation) for that target and the robot should communicate a
> composed response using the existing `SPEAK` command.

**INT-09 — Unknown Request**
> Given a student asks something outside the system's scope,
> When the system cannot classify the request with sufficient
> confidence,
> Then the robot should clearly decline rather than guessing, using the
> existing `SPEAK` command.

**INT-10 — Destination Not Found**
> Given a student asks for a location that has no registered content,
> When Guide or Navigation cannot resolve it,
> Then the robot should say so honestly rather than inventing
> information, using the existing `SPEAK` command.

Acceptance criteria intentionally reference only externally observable
behavior (what the robot says/does) and existing, named contract types
— never internal function names, file paths, or private state.

## 13. Traceability matrix

| Scenario | Required Capability | Module(s) | Future Integration Point | Priority |
|---|---|---|---|---|
| INT-01 | Stable-presence greeting | Vision, Decision, Robot | *(already integrated)* | MVP |
| INT-02 | Free-text information lookup | ML, Decision, Guide, Robot | `app.main` | MVP |
| INT-03 | Free-text navigation request | ML, Decision, Navigation, Robot | `app.main` | MVP |
| INT-04 | Combined request fan-out/compose | ML, Decision, Guide, Navigation, Robot | `app.main` | MVP |
| INT-05 | Help/assistance intent | ML, Decision, Robot | `app.main` | MVP |
| INT-06 | Session context memory | ML, Decision, Guide | `app.main` / future Decision extension | Nice-to-have |
| INT-07 | Arabic content + classification | ML, Guide, Robot | `app.main` | Nice-to-have |
| INT-08 | English baseline | ML, Decision, Guide, Navigation, Robot | `app.main` | MVP |
| INT-09 | Low-confidence fallback | ML, Decision, Robot | `app.main` | MVP |
| INT-10 | Unresolvable-target fallback | ML, Decision, Navigation, Robot | `app.main` | MVP |
| INT-11 | Post-navigation session close | Decision, Robot | `app.main` | Nice-to-have |
| INT-12 | General session close | Decision, Robot | *(already integrated)* | MVP |

## 14. MVP vs. Nice-to-have

**MVP:** INT-01, INT-02, INT-03, INT-04, INT-05, INT-08, INT-09,
INT-10, INT-12 (Greeting, Information, Navigation, Combined request,
Help, English baseline, Unknown-request fallback,
Destination-not-found fallback, Session completion). **9 scenarios.**

**Nice-to-have:** INT-06 (Context-aware follow-up), INT-07 (Arabic),
INT-11 (Navigation completion as a distinct scenario from general
session completion). **3 scenarios.**

This split exists to prevent scope explosion during future
integration — an `app.main` extension that only ever implements the 9
MVP scenarios still delivers a complete, usable assistant.

## 15. Future extensibility

New scenarios are added the same way INT-01 through INT-12 were
written: as a new row following the Section 3 schema, with realistic
examples and explicit "future" markers for anything not yet
implemented. Adding a scenario should **never** require rewriting an
existing module — only adding documentation (and, where useful,
additional acceptance-criteria coverage in
`tests/test_interaction_scenarios.py`).

Planned future scenarios (specification only, not written up in detail
here):

- **INT-13 — Nearby Places** ("what else is near the AI Lab?")
- **INT-14 — Recommendation** ("what's a good place to study?")
- **INT-15 — Accessibility Assistance** (e.g. wheelchair-accessible routes)

## 16. Prototype data disclaimer

All university locations referenced in this document (AI Lab, Library,
Engineering Building, Student Affairs, etc.) are the existing
**prototype** entries in `app.guide.locations.LOCATION_CONTENT` (Guide
G1 phase). They do not describe any real university's actual buildings,
floors, services, or opening hours — see that module's own disclaimer
for the authoritative statement.

## 17. Related documentation

- [`docs/architecture.md`](architecture.md) — overall module architecture and ownership
- [`docs/contracts.md`](contracts.md) — communication philosophy and dependency rules
- [`docs/guide.md`](guide.md) — Guide's topic and location flows in detail
- [`docs/integration_contract.md`](integration_contract.md) — the full Phase 1–7 integration history and existing contract definitions
