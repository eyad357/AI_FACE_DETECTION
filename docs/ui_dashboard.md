# UI Dashboard — Production Demo Dashboard

## What this is

A Streamlit-based control-center dashboard over the existing,
already-integrated AI University Lab Guide system. It is a
**presentation and orchestration layer only** — it owns no domain
logic. Every panel is populated by calling real, existing application
services through a thin adapter boundary.

## Launch

From the repository root, with `requirements.txt` installed:

```
streamlit run app/ui/dashboard.py
```

No other setup is required. The dashboard never requires physical
robot hardware or a physical camera to run — see "Hardware vs
simulation" below.

## Architecture

```
app/ui/
    dashboard.py            Streamlit presentation layer (widgets only, no logic)
    dashboard_service.py    Orchestrator: composes adapters, builds view data
    dashboard_view_models.py  Plain dataclasses the dashboard renders
    adapters/
        vision_adapter.py       wraps app.vision.Camera / FaceDetector
        ml_adapter.py           wraps app.ml.service.MLIntentService
        dl_adapter.py           wraps app.dl.service.GestureRecognitionService
        decision_adapter.py     wraps app.decision.state_manager.StateManager
        guide_adapter.py        wraps app.guide.GuideService
        navigation_adapter.py   wraps app.navigation.service.NavigationService
        speech_adapter.py       wraps app.speech.ConversationService
        robot_adapter.py        wraps app.integration.RobotIntegrationAdapter
```

Dependency direction: `dashboard.py` → `dashboard_service.py` →
`app.ui.adapters.*` → the existing domain packages. Nothing in this
phase imports `app.main`, redefines an existing domain contract
(`RobotCommandType`, `GuideTopic`, `RouteResult`, ...), or creates a
second implementation of routing/speech/decision/ML/DL logic.
Enforced by `tests/ui/test_dashboard_isolation.py` (an AST-based
static audit, not just a convention).

Existing Route Display logic (`app.ui.route_display`,
`app.ui.view_models`) is **reused, not duplicated** — the navigation
and guide adapters call `build_navigation_view_safe` and
`guide_response_to_view` directly.

## Data flow

1. **Perception** — clicking "Capture frame" opens the real `Camera`,
   reads one frame, runs the real `FaceDetector`, and releases the
   camera immediately (no device is held open between refreshes).
2. **Interaction** — a typed utterance goes through the real
   `MLIntentService` (if the trained artifact is present) and then the
   real `ConversationService`, exactly as any other caller would
   compose ML + Speech.
3. **Navigation** — an origin/destination pair goes through the real
   `NavigationService.find_route`, and the resulting `RouteResult` is
   rendered with the existing `build_navigation_view_safe` view
   builder.
4. **Guide** — a topic goes through the real `GuideService`, rendered
   with the existing `guide_response_to_view` view builder.
5. **Robot** — every button (Greet, Wave, Idle, Stop, Speak, Explain
   AI/Robotics/Training/Lab) calls the corresponding method on the
   real `RobotIntegrationAdapter`, which delegates to
   `RobotController`. No new command vocabulary was introduced.
6. **Event timeline** — every one of the above actions appends a real
   `EventRecord` to the in-memory session log. The timeline starts
   empty and only ever reflects things that actually happened in the
   current session; no historical events are pre-seeded.

## Demo mode

The Robot panel and all "Demo Scenarios" always run against
`app.robot.SimulatedRobotBackend` (the project's existing simulation
capability) rather than any physical robot backend. This is stated
directly in the UI ("DEMO / SIMULATION MODE"). Demo mode:

- **does** trigger real project services and display their real
  outputs (real `RouteResult`, real `GuideResponse`, real
  `ConversationResponse`, real `RobotExecutionResult`)
- **does not** fabricate a successful backend result, bypass any
  contract, mutate persistent state, or require hardware

## Hardware vs. simulation behavior

| Subsystem   | In this environment                                             |
|-------------|-------------------------------------------------------------------|
| Camera      | Usually unavailable (no device) — the Perception panel reports this honestly instead of inventing a detection. |
| ML          | Real, runs on the trained artifact if present under `app/ml/artifacts`. |
| DL          | Real service; reports `model_source` honestly (trained artifact vs. untrained fixture). |
| Navigation / Decision / Guide / Speech | Pure Python, always fully available. |
| Robot       | Always `SimulatedRobotBackend` — never drives physical hardware from this dashboard. |

## Known limitations

- DL (gesture recognition) has no live camera-driven inference path in
  the dashboard, because that requires a real frame source this
  environment does not have. The panel surfaces the model's real
  status/info instead of a fabricated prediction.
- Vision's `capture_and_detect` will typically report "camera
  unavailable" in a headless server/demo environment — this is by
  design, not a bug: it never substitutes a fake detection.
- The event timeline is per-session and in-memory; it is not persisted
  across dashboard restarts.

## Troubleshooting

- **"Camera unavailable"** — expected in a headless environment. Any
  environment with an actual OS-visible camera device (index 0) will
  report `PASS` instead.
- **ML/DL card shows DEGRADED/UNAVAILABLE** — no trained artifact was
  found at the expected path; the subsystem still functions with its
  fallback behavior (heuristic ML fallback / untrained DL fixture),
  which is reported honestly rather than hidden.
- **Streamlit does not start** — confirm `streamlit>=1.30,<2` from
  `requirements.txt` is installed (`pip install -r requirements.txt`).

## Integration boundaries

This phase does not modify Vision, ML, DL, Navigation, Decision,
Guide, Speech, Robot, or Integration internals. All new code lives
under `app/ui/` and `tests/ui/`. See
`docs/PHASE_REPORT_ui_dashboard.md` for the full accounting of files
added/modified and the static audit results.
