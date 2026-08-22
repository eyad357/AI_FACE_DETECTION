# Robot Gestures — Phase Documentation

## Purpose

The gesture layer provides a gesture-level abstraction (`GestureIntent`
/ `GestureRequest`) on top of the existing, unmodified Robot module. It
lets a caller ask for a human-meaningful gesture (e.g. "wave at the
visitor") without needing to know the underlying `RobotCommandType`
vocabulary, while guaranteeing that execution still goes through the
existing `RobotController` — the Robot module's one public execution
boundary — exactly as before this phase.

This phase does **not** decide *when* a gesture should occur (that
remains Decision's / the future `app.main` orchestrator's
responsibility, unchanged), does not talk to hardware directly, and
does not introduce a second Robot controller or backend abstraction.

## Files

```
app/robot/gesture_definitions.py   # GestureIntent, GestureRequest, GestureError, validation
app/robot/gesture_mapper.py        # GestureIntent -> existing RobotCommandType mapping
app/robot/gesture_controller.py    # GestureController: dispatches via the existing RobotController
tests/test_robot_gestures.py       # tests for this phase only
docs/robot_gestures.md             # this file
```

None of the existing `app/robot/robot_commands.py` or
`app/robot/robot_controller.py` files were modified. `app/robot/__init__.py`
was also left unmodified — this phase's public symbols are imported
directly from their own modules
(`from app.robot.gesture_controller import GestureController`, etc.),
exactly the same way tests already import from
`app.robot.robot_controller` today.

## Supported gestures

`GestureIntent` defines six gesture-level intents, as requested for
this phase: `WAVE`, `POINT`, `ACKNOWLEDGE`, `THINKING`, `ARRIVED`,
`IDLE`.

Only gestures with an unambiguous, already-existing `RobotCommandType`
counterpart are mapped to an executable command:

| GestureIntent | Existing RobotCommandType | Status |
|---|---|---|
| `WAVE` | `RobotCommandType.WAVE` | Supported |
| `IDLE` | `RobotCommandType.IDLE` | Supported |
| `POINT` | — | Unsupported (see below) |
| `ACKNOWLEDGE` | — | Unsupported (see below) |
| `THINKING` | — | Unsupported (see below) |
| `ARRIVED` | — | Unsupported (see below) |

`POINT`, `ACKNOWLEDGE`, `THINKING`, and `ARRIVED` have no existing
`RobotCommandType` that safely and unambiguously expresses them:

- `POINT` implies directional/spatial motion; no existing command
  carries direction.
- `ACKNOWLEDGE` and `THINKING` are visually distinct from `GREET`
  (which is a specific, already-defined visitor greeting action) —
  force-mapping them onto `GREET` would misrepresent what the robot
  actually does when `GREET` is requested elsewhere in the system.
- `ARRIVED` is ambiguous between `STOP` (halt motion) and `IDLE` (go to
  idle state); picking either would be guessing at a semantic the
  existing vocabulary was never designed to carry.

Per this phase's strict rules, new `RobotCommandType` values are not
added to resolve these gaps. Instead, requesting one of these four
gestures returns a `GestureExecutionResult(success=False, ...)` with a
clear message — the request never reaches `RobotController` or the
backend. See "Integration limitations" below and `PHASE_REPORT.md`.

## Gesture validation

`GestureRequest(gesture: GestureIntent, text: Optional[str] = None,
metadata: Dict[str, Any] = {})` is validated by
`validate_gesture_request()`, which raises `GestureError` (a
programmer/configuration error, mirroring `RobotError`) if the request
is not a `GestureRequest` or its `gesture` field is not a
`GestureIntent` member. Normal, expected outcomes — an unsupported
gesture, or a downstream `RobotCommand` execution failure — are never
raised as exceptions; they are reported via
`GestureExecutionResult(success=False, ...)`, exactly mirroring how
`RobotController.execute()` already fails safely for `RobotCommand`s.

## Gesture mapping behavior

`app.robot.gesture_mapper` holds a single, explicit mapping table
(`GESTURE_TO_ROBOT_COMMAND`) from every `GestureIntent` to either an
existing `RobotCommandType` or `None`. `map_gesture_to_command()` and
`is_gesture_supported()` are pure, side-effect-free lookups against
this table. The mapping never introduces, renames, or removes a
`RobotCommandType` member — it only reuses what already exists.

## Relationship with the existing `RobotController`

`GestureController` wraps an existing `RobotController` instance by
composition (`GestureController(robot_controller=...)`, defaulting to
`RobotController()` — the same default the existing Robot module
already uses). For every supported gesture, `GestureController`:

1. Validates the `GestureRequest`.
2. Looks up the existing `RobotCommandType` for the gesture.
3. Builds a `RobotCommand` from it (forwarding `text`/`metadata`
   as-is).
4. Calls the existing `RobotController.execute()` — the same public
   method every other caller (including `app.main`) already uses.

`GestureController` never talks to a `RobotBackend` directly, never
constructs its own `SimulatedRobotBackend`, and never bypasses
`RobotController.execute()`. It is a thin, gesture-aware adapter in
front of the Robot module's existing execution boundary — not a second
Robot controller.

## Relationship with the existing backend abstraction

`GestureController` has no knowledge of which `RobotBackend` the
wrapped `RobotController` uses (`SimulatedRobotBackend`, or any future
hardware backend). Backend selection remains entirely `RobotController`'s
responsibility, unchanged by this phase.

## Hardware isolation

Exactly like the existing Robot module, the gesture layer requires no
physical hardware, no Robot SDK, no network access, and no external
API to run or to be tested. `GestureController()` with no arguments
works anywhere `RobotController()` already works, including CI.

## Forbidden dependencies

`app/robot/gesture_definitions.py`, `gesture_mapper.py`, and
`gesture_controller.py` do not import `app.vision`, `app.ml`, `app.dl`,
`app.navigation`, `app.decision`, or `app.main`. They depend only on
the Python standard library, the existing `app.robot.robot_commands`
/ `app.robot.robot_controller` modules, this phase's own gesture
modules, and `app.utils.logger` (the same logging dependency the
existing Robot module already uses). This is verified by
`tests/test_robot_gestures.py::TestNoForbiddenImports`.

## Extension points for future gestures

To support a currently-unsupported gesture (or a new one) in the
future without weakening this phase's guarantees:

1. If an existing `RobotCommandType` already expresses it, add one
   entry to `GESTURE_TO_ROBOT_COMMAND` in `gesture_mapper.py` — no
   other change required.
2. If no existing `RobotCommandType` expresses it, that is a genuine
   gap in the shared Robot command vocabulary, not something this
   phase can or should resolve by inventing a mapping. Per the Robot
   Gestures phase rules, adding a new `RobotCommandType` requires
   explicit, separate approval and must be proposed against
   `app/robot/robot_commands.py` directly — not silently added from
   within the gesture layer.
3. Gesture sequencing (`GestureController.execute_sequence()`) already
   supports ordered multi-gesture requests; no new abstraction is
   needed for future gestures to participate in a sequence.

## Integration limitations

See `PHASE_REPORT.md`, section "Integration gaps", for the full
reasoning behind `POINT`, `ACKNOWLEDGE`, `THINKING`, and `ARRIVED`
currently having no safe existing-command mapping, and what would be
required (a `RobotCommandType` addition, separately approved) to
support them.
