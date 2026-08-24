# Presentation Demo — AI University Lab Guide

## What this is
A simplified, professor-facing presentation screen built **on top of**
the existing technical dashboard's `DashboardService` and adapters
(`app/ui/dashboard_service.py`, `app/ui/adapters/*`). It reimplements
no business logic — it only orchestrates the same real service calls
the technical dashboard uses, behind a much simpler screen.

`app/ui/dashboard.py` (the technical dashboard) is unchanged and still
available.

## Launch

```
python -m streamlit run app/ui/demo.py
```

Technical dashboard (unchanged, still available):

```
python -m streamlit run app/ui/dashboard.py
```

## Primary demo flow

```
Camera → Face Detection → Welcome → Robot Greeting (wave)
   → Student Question → Speech/ML understanding → Decision
   → Guide OR Navigation → Robot Response → Result
```

1. **Capture** — calls the real Vision adapter (`Camera` + `FaceDetector`). On a
   real detection, the demo feeds a Decision-compatible reconstruction
   of that same real result into `DashboardService.decision` and
   triggers the real `RobotIntegrationAdapter.greet()` /
   `.wave()` actions.
2. **Ask Assistant / demo buttons** — the typed (or button-supplied)
   text goes through `DashboardService.handle_utterance`, which is the
   same real ML → Speech pipeline the technical dashboard uses.
3. **Navigation** — when Speech classifies the turn as
   `NAVIGATION_CONFIRMATION` with a resolved destination, the demo
   calls the real `NavigationService.find_route` and renders the real
   `RouteResult`.
4. **Guide topics** — "Ask about AI / Robotics / Training" call the
   real `GuideService.get_topic_content` and then the matching real
   `RobotIntegrationAdapter.explain_*` method.
5. **Result / pipeline** — a simplified 5-stage indicator (Vision,
   Understanding, Decision, Navigation, Robot) reflects only whether
   that stage actually ran this turn — never a fabricated "PASS".

## Available demo scenarios (buttons)
Welcome, Ask about AI, Ask about Robotics, Ask about Training,
Find AI Lab, Arabic Demo. Each supplies a demo **input string** only
— the result always comes from the real services above.

Demo phrasing note: the destination-extraction pattern in
`app.speech.conversation` recognizes navigation phrasing such as
*"Take me to the AI Lab"* / *"Guide me to..."* / *"Navigate to..."*,
not *"Where is..."* (which is the informational/topic phrasing). The
"Find AI Lab" button therefore uses *"Take me to the AI Lab"* so the
demo reliably reaches `NAVIGATION_CONFIRMATION` with a real route,
rather than a clarification prompt. This is an existing, unmodified
Speech behavior — documented here for presenters, not changed.

## Camera behavior
Uses the same `Camera` class as the technical dashboard, opened and
released on a single button press (no handle held open across
Streamlit reruns). If no camera device exists, the panel shows
"Camera unavailable — continuing in Demo Mode" and the rest of the
flow (interaction, navigation, robot) continues to work normally.

## Robot simulation
All robot actions run on `app.robot.SimulatedRobotBackend` via the
existing `RobotIntegrationAdapter` — identical to the technical
dashboard. No physical hardware is required or claimed.

## Limitations
- Live camera-driven face detection depends on a real OS camera device
  being present; in a headless environment the demo runs in Demo Mode
  for that stage only.
- The Decision state machine's `GREETING` state transition requires
  its own internal debounce logic (unchanged); the presentation always
  triggers the real Robot greet/wave actions directly regardless, so
  the on-screen greeting is never blocked by that debounce.
- DL (gesture) live inference is not wired into this screen for the
  same reason it isn't in the technical dashboard: no camera-driven
  frame source in this environment.
