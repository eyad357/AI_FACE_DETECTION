# Speech & Conversation Module (`app/speech`)

## Status

**Implemented — independent phase.** Owned by Person 2 (Robotics /
Interaction), per `docs/contracts.md`'s Ownership table ("Speech" is
listed under Person 2). Scaffolding for `app/ml`, `app/dl`,
`app/navigation`, and `app/ui` is untouched and unaffected by this
phase.

## Purpose

`app/speech` answers one question: **"What should the robot SAY next,
in text?"** Given a student's free-text utterance (and optional
caller-provided context), it produces a single, language-appropriate
text reply plus an updated lightweight conversation state.

It does **not**:

- Decide whether/when to greet a visitor (`app.decision`'s job).
- Classify intent statistically (`app.ml`'s job — not implemented in
  this phase; see "Integration gaps" below).
- Compute routes (`app.navigation`'s job — not yet implemented).
- Hold or own factual guide content (`app.guide`'s job).
- Perform speech synthesis or drive any hardware
  (`app.robot`'s job — not implemented or called by this phase).
- Orchestrate the application (`app.main`'s job — not implemented or
  called by this phase).

## Public contracts

All four live under `app.speech` (imported directly from the package,
e.g. `from app.speech import ConversationService`):

### `ConversationInput` (`app.speech.conversation`)

| Field | Type | Meaning |
|---|---|---|
| `text` | `str` | The student's raw utterance. May be malformed — `handle()` never raises. |
| `language` | `Optional[Language]` | Explicit language override. |
| `intent` | `Optional[app.models.schemas.IntentType]` | Caller-provided, already-classified intent (e.g. from a future `app.ml.service.MLIntentService.predict()` call). |
| `context` | `Optional[ConversationContext]` | Previous turn's context, to continue a conversation. `None` starts a fresh one. |
| `information_text` | `Optional[str]` | Caller-supplied content to speak for an INFORMATION turn (e.g. `GuideResponse.spoken_text`). Takes precedence over this module's own placeholder knowledge. |
| `destination` | `Optional[str]` | Caller-supplied destination/topic name, taking precedence over local text extraction. |

### `ConversationResponse` (`app.speech.response`)

| Field | Type | Meaning |
|---|---|---|
| `spoken_text` | `str` | Plain text for a future orchestration layer to hand to Robot/UI. |
| `response_type` | `ConversationResponseType` | GREETING / INFORMATION / NAVIGATION_CONFIRMATION / CLARIFICATION / CONFIRMATION_ACK / HELP / FALLBACK_UNKNOWN / MALFORMED_INPUT / CONTEXT_RESET. |
| `language` | `Language` | Language `spoken_text` is written in. |
| `context` | `ConversationContext` | Updated context — pass back into the next `ConversationInput`. |
| `requires_clarification` | `bool` | True while the system is waiting on an answer to a clarification question. |
| `timestamp` | `datetime` | UTC time the response was produced. |

### `ConversationContext` (`app.speech.context`)

Immutable (frozen) dataclass: `language`, `current_topic`,
`current_destination`, `last_intent`, `last_user_text`,
`pending_clarification`, `turn_count`. Built fresh via
`ConversationContext.initial()`; never mutated in place — every turn
returns a new instance via `dataclasses.replace` (`with_updates()`).

### `Language` (`app.speech.language`)

`Language.ENGLISH` / `Language.ARABIC`. `detect_language(text)` is a
deterministic, offline heuristic (Arabic Unicode block presence) — no
external language-detection library or network call.

## Input format

Free-text `str`. No structured command syntax is required. Malformed
input (`None`, non-`str`, empty, or whitespace-only) is handled
gracefully — `ConversationService.handle()` never raises; it returns a
`MALFORMED_INPUT` response asking the student to repeat themselves.

## Output format

A single `ConversationResponse`. `spoken_text` is always a non-empty,
plain string in the resolved `language`.

## Context behavior

- **Short contextual follow-up:** if a navigation request doesn't name
  a destination (e.g. "Can you guide me there?"), the last
  `current_destination` or `current_topic` is reused. Pronoun words
  ("there", "it", "that", "here", `هناك`) are treated as references to
  context, not literal destination names.
- **Clarification:** if neither the caller nor local extraction can
  determine a destination/topic, `pending_clarification` is set
  (`"destination"` or `"topic"`) and the *next* turn's raw text is
  used directly as the answer, without being re-classified.
- **Reset:** saying "start over" / "reset" / `من جديد` (or calling
  `ConversationService.reset(context)`) returns a brand-new context,
  preserving the established language by default.

## Language behavior

- Explicit `ConversationInput.language` always wins.
- Otherwise, Arabic-script text in the current turn switches the
  conversation to Arabic.
- Otherwise, the conversation continues in `context.language` (so a
  student typing plain ASCII mid-Arabic-conversation, e.g. a proper
  noun, doesn't accidentally flip the language back to English).
- A brand-new context defaults to `Language.ENGLISH`.
- Every phrase key in `app.speech.language.PHRASES` has both an
  English and an Arabic entry (enforced by
  `tests/speech/test_language.py::TestPhraseTable`).

## Clarification behavior

Produced when a NAVIGATION or INFORMATION request is missing the
information needed to answer (no destination / no topic, and no
caller-supplied fallback). `response_type=CLARIFICATION`,
`requires_clarification=True`, and `context.pending_clarification` is
set so the next turn is interpreted as the answer.

## Confirmation behavior

Two distinct things are both called "confirmation" in the phase
brief, and both are implemented:

1. **Navigation confirmation** — acknowledging a guide request, e.g.
   "Sure. I'll guide you to the library."
   (`response_type=NAVIGATION_CONFIRMATION`).
2. **Yes/No acknowledgement** — a short standalone "yes"/"no"/`نعم`/`لا`
   reply is acknowledged (`response_type=CONFIRMATION_ACK`).

## Isolation guarantees

Enforced both by code review and by
`tests/speech/test_isolation.py` (AST-based static checks, plus a
runtime check that importing `app.speech` never pulls in `app.robot`
or `app.ml` as a side effect):

- `app/speech/**/*.py` never imports `app.robot`, `app.ml`,
  `app.vision`, `app.dl`, or `app.main`.
- No file in `app/speech` references `RobotCommandType` or constructs
  a `RobotCommand` — this module produces text only.
- No network/socket module is imported anywhere in the package.
- Given the same `ConversationInput`, `handle()` always returns the
  same `ConversationResponse.spoken_text` / `response_type` (fully
  deterministic, no hidden state, no randomness, no clock-dependent
  branching).

## Integration gaps discovered

1. **No ML intent classifier is wired in.** `app/ml` already has a
   working `MLIntentService`/`IntentResult`/`IntentType` (see
   `app/ml/service.py`), and `ConversationInput.intent` accepts an
   `IntentType` directly for exactly this reason — but no orchestrator
   in this phase actually calls `MLIntentService.predict()` and feeds
   the result in. That wiring belongs to a future `app.main`
   integration phase (mirroring how Guide/Robot were only wired
   together in Phase 7). Until then, `app.speech` falls back to its
   own tiny local keyword heuristic (`_infer_local_intent` in
   `conversation.py`) so it remains independently usable.
2. **No Guide/Navigation wiring.** Similarly, `ConversationInput`
   accepts `information_text` (for Guide-sourced content) and
   `destination` (for a future Navigation-sourced route), but no
   orchestrator in this phase calls
   `GuideService.get_topic_content()` or a Navigation service and
   passes the result in. `app.navigation` is not implemented yet
   (still scaffolded — see `app/navigation/service.py`), so there is
   nothing to integrate with even if this phase wanted to.
3. **Placeholder local knowledge (`app/speech/knowledge.py`).** To
   make the phase's own worked example ("Where is the AI Lab?" → "The
   AI Lab is on the second floor of the Engineering Building.") work
   when `app.speech` is exercised standalone (no caller-provided
   `information_text`), a small, explicitly-labeled placeholder
   lookup table was added. This is **not** meant to be a permanent
   content source — real content should always come from
   `GuideResponse.spoken_text` via `ConversationInput.information_text`
   once an orchestrator exists to provide it.
4. **`IntentType.COMBINED` is treated as NAVIGATION-priority.** The ML
   module's `IntentType` includes `COMBINED` (both information and
   navigation in one utterance). This phase handles one intent per
   conversational turn, so a `COMBINED` caller-provided intent is
   mapped to the NAVIGATION handler. A future phase could instead
   split a `COMBINED` intent into two sequential `ConversationResponse`
   turns.

None of the above required modifying any protected module — every gap
is closed either by a Speech-owned local adapter (`knowledge.py`,
`_infer_local_intent`) or by an input field a future caller can supply
(`intent`, `information_text`, `destination`).

## Future integration expectations

A future `app.main` (or equivalent) orchestration phase is expected to:

```python
from app.speech import ConversationInput, ConversationService
from app.ml.service import MLIntentService          # optional
from app.guide import GuideService                    # optional
from app.robot import RobotController, RobotCommand, RobotCommandType

speech = ConversationService()
context = None  # or a previously stored ConversationContext

intent_result = MLIntentService().predict(student_text)   # optional
response = speech.handle(ConversationInput(
    text=student_text,
    intent=intent_result.intent,
    context=context,
    # information_text=guide_service.get_topic_content(topic).spoken_text,
))
context = response.context  # carry forward to the next turn

robot.execute(RobotCommand(RobotCommandType.SPEAK, text=response.spoken_text))
```

This wiring is intentionally **not implemented** in this phase (see
"STRICT CHANGE RULE" — `app/main.py` is protected).
