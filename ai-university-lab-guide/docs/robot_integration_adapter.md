# Robot Integration Adapter — Phase Documentation

## Purpose

`RobotIntegrationAdapter` is a thin translation boundary between
high-level, application-level Robot-facing actions (e.g. "greet the
visitor", "say this", "explain this topic") and the existing,
unmodified `app.robot` public API. It exists so a future caller (a
Decision/orchestration layer, a UI, a test harness) can request an
action by name without needing to construct a `RobotCommand` or know
the `RobotCommandType` vocabulary directly — while every action still
flows through the same existing `RobotController` boundary that every
other caller already uses.

This phase does **not** decide *when* an action should occur (that
remains Decision's / `app.main`'s job, unchanged), does not fetch
Guide content, does not classify intent, does not calculate routes,
and does not talk to hardware directly. It is not wired into
`app.main` — see "Future integration expectations" below.

## Files

```
app/integration/__init__.py            # re-exports RobotIntegrationAdapter, AdapterError
app/integration/robot_adapter.py       # RobotIntegrationAdapter, AdapterError
tests/test_robot_integration_adapter.py  # tests for this phase only
docs/robot_integration_adapter.md      # this file
```

No existing `app/robot/` file was modified — the adapter depends only
on `app.robot`'s existing public API (`RobotController`, `RobotCommand`,
`RobotCommandType`, `RobotExecutionResult`), imported exactly the way
`app.main` and `tests/test_robot.py` already import it.

## Adapter public API

One high-level method per existing `RobotCommandType` member — nine
methods for nine existing commands, no more, no fewer:

```python
from app.integration import RobotIntegrationAdapter

adapter = RobotIntegrationAdapter()

adapter.execute_greeting()          # -> RobotController.greet()          (GREET)
adapter.wave()                      # -> RobotController.wave()           (WAVE)
adapter.speak(text)                 # -> RobotController.speak(text)      (SPEAK)
adapter.idle()                      # -> RobotController.idle()           (IDLE)
adapter.stop()                      # -> RobotController.stop()           (STOP)
adapter.explain_ai(text)            # -> RobotController.execute(RobotCommand(EXPLAIN_AI, text=text))
adapter.explain_robotics(text)      # -> ... EXPLAIN_ROBOTICS ...
adapter.explain_training(text)      # -> ... EXPLAIN_TRAINING ...
adapter.explain_lab(text)           # -> ... EXPLAIN_LAB ...
```

Every method returns the existing `app.robot.RobotExecutionResult`
directly (`command_type`, `success`, `message`) — the adapter does not
wrap, rename, or duplicate that result contract.

`RobotIntegrationAdapter(robot_controller: Optional[RobotController] =
None)` defaults to `RobotController()` (the existing default,
hardware-free `SimulatedRobotBackend`), or accepts an existing
`RobotController` instance so the adapter participates in whatever
Robot execution boundary the caller has already set up.

## Relationship with the existing Robot public API

`GREET`, `WAVE`, `SPEAK`, `IDLE`, and `STOP` already have convenience
wrappers on `RobotController` itself (`greet()`, `wave()`, `speak()`,
`idle()`, `stop()`); the adapter's corresponding methods call those
wrappers directly. The four `EXPLAIN_*` topics have no such
convenience wrapper on `RobotController` — a caller must otherwise
build a `RobotCommand(EXPLAIN_AI, text=...)` and call `execute()`
directly. The adapter's `explain_ai()` / `explain_robotics()` /
`explain_training()` / `explain_lab()` methods provide that same
translation as a named method, using only the existing `RobotCommand`
and `RobotCommandType.EXPLAIN_*` members — no new command type, no new
command object shape.

The adapter never talks to a `RobotBackend` directly, never
constructs `SimulatedRobotBackend` or any other backend itself, and
never bypasses `RobotController.execute()` / its convenience wrappers.
It is not a second Robot controller.

## Supported high-level actions

See "Adapter public API" above — all nine existing `RobotCommandType`
members are covered.

## Unsupported actions and why

The phase brief's conceptual examples included `show_navigation_step(...)`
and `show_arrival()`. Neither is exposed by the adapter:

- **`show_navigation_step(...)`** — `app.navigation.service` is an
  explicit, documented **placeholder** in this repository ("PLACEHOLDER
  — not implemented in this phase"), and no `RobotCommandType` member
  corresponds to a navigation step. There is nothing existing to
  translate this action into.
- **`show_arrival()`** — no existing `RobotCommandType` member
  unambiguously represents "the robot/visitor has arrived." `STOP`
  (halt motion) and `IDLE` (at-rest state) are both plausible but
  semantically different guesses, and the existing vocabulary was
  never documented as distinguishing them for this purpose. Guessing
  would misrepresent what the underlying command actually does
  elsewhere in the system.

Per the strict change rules for this phase, no new `RobotCommandType`
value was added to support these, and neither method was added with a
"best guess" mapping. `hasattr(adapter, "show_navigation_step")` and
`hasattr(adapter, "show_arrival")` are both `False`, and this is
verified by `tests/test_robot_integration_adapter.py::
TestUnsupportedActionsAreNotExposed`.

## Input validation

The adapter validates exactly one thing at its own boundary: that any
`text` argument (`speak`, and the four `explain_*` methods) is either
a `str` or `None`. A non-string, non-`None` value (e.g. an `int`,
`list`, or `float`) raises `AdapterError` — a programmer/configuration
error, mirroring `RobotController`'s own `RobotError` for its
equivalent "not a `RobotCommand`" case.

Content-level validation — rejecting empty or whitespace-only speech
text — is deliberately **not** duplicated in the adapter. The existing
`RobotController.execute()` already performs that check and reports it
as a normal, non-raising `RobotExecutionResult(success=False, ...)`;
re-implementing the same check in the adapter would risk the two
copies silently diverging over time. `None` and `""` are both valid
`Optional[str]` values as far as the adapter is concerned and are
forwarded to the existing controller unchanged.

## Error handling / result behavior

- **Adapter-level input errors** (wrong type for `text`) raise
  `AdapterError` — mirrors `RobotError`'s "invalid input" semantics,
  never silently coerced or ignored.
- **Normal Robot execution outcomes** (empty speech text, a backend
  failure) are never raised as exceptions. The adapter returns
  whatever `RobotExecutionResult` the existing `RobotController`
  already produced — `success=False` with a descriptive `message`,
  exactly as calling `RobotController` directly would produce. The
  adapter does not corrupt, alter, or intercept application state on a
  failure; it is a pure pass-through of the existing, already-correct
  fail-safe behavior.
- **No new result contract was introduced.** `RobotExecutionResult`
  (from `app.robot.robot_controller`) already fit the adapter's needs
  exactly, so it is returned as-is rather than wrapped in a new
  adapter-specific type.

## Dependency isolation

`app/integration/__init__.py` and `app/integration/robot_adapter.py`
import only: the Python standard library, the existing `app.robot`
public API, and `app.utils.logger`. They do not import `app.vision`,
`app.ml`, or `app.dl` (strictly forbidden), and they also avoid
importing `app.decision`, `app.guide`, `app.navigation`, and
`app.main` (discouraged, and not needed — every adapter method takes
its data, e.g. `text`, as a plain method argument rather than fetching
it from another workstream). Verified by
`tests/test_robot_integration_adapter.py::TestDependencyIsolation` via
AST inspection of both files.

## `main.py` orchestration boundary

`app/main.py` was **not modified** and remains the only orchestration
layer in the project. The adapter is not called from `app.main` in
this phase — wiring it in is explicitly out of scope ("Future
integration into `main.py` is outside this phase").

## Future integration expectations

A future phase could have `app.main.ApplicationIntegration` construct
one `RobotIntegrationAdapter` (wrapping the same `RobotController` it
already owns) and call its named methods instead of building
`RobotCommand`s inline — e.g. replacing
`robot_controller.execute(RobotCommand(RobotCommandType.GREET))` with
`adapter.execute_greeting()`. That change is not made here; making it
would mean modifying `app/main.py`, which is explicitly protected in
this phase. No signature or behavior decision made in this phase
should need to change to support that future wiring — every adapter
method already returns the same `RobotExecutionResult` shape
`app.main` already consumes today.
