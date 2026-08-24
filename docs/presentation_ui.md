# Presentation UI — AI University Lab Guide

## What this is
The polished, professor-facing screen at `app/ui/demo.py`. It is a
**thin presentation layer** on top of the existing
`app.ui.dashboard_service.DashboardService` and its adapters — it holds
no business logic and never fabricates a result. The separate
technical dashboard (`app/ui/dashboard.py`) is unchanged and still
available for development/debugging use.

## Launch
```
python -m streamlit run app/ui/demo.py
```

## Flow
```
CAMERA
  → "Looking for you..."
  → real Vision capture + detection
  → "✓ Face detected" → "Welcome to AI University Lab!" (real robot GREET/WAVE)
ASSISTANT
  → welcome card + free-text ask box + quick demo buttons
  → real Guide / Navigation / Speech result in a clean card
  → friendly robot-status pill (e.g. "🤖 Speaking", "🤖 Explaining")
```
A "↻ Restart Demo" button returns to the camera stage for repeat
live demos without restarting the process (the underlying
`DashboardService` — and its already-loaded ML/DL/Guide/Navigation/
Speech/Robot components — is cached for the whole session).

## Screen 1 — Camera / Welcome
- Uses Streamlit's native `st.camera_input` widget, which opens a
  **real, live viewfinder in the presenter's own browser** (a genuine
  `getUserMedia` permission prompt + continuous preview + shutter
  button) — this is what actually makes the camera feed visible;
  a prior version used a server-side `cv2.VideoCapture` grab whose
  frame was read and then discarded without ever being displayed.
- On capture, the photo is decoded and passed straight into the same,
  unmodified, real `FaceDetector` via
  `DashboardService.analyze_photo()` → `VisionAdapter.detect_in_frame()`
  — no detection is ever invented. `DashboardService.refresh_perception()`
  / `VisionAdapter.capture_and_detect()` (the `Camera`-based path) are
  unchanged and still power the technical dashboard.
- On a real detection, the same real `DetectionResult` shape is fed
  into `DashboardService.decision` and the real
  `RobotIntegrationAdapter.greet()` / `.wave()` actions run.
  A content hash of the captured photo guarantees this only happens
  once per capture, even across unrelated Streamlit reruns.
- If the camera/photo is unavailable or unreadable, or no face is
  found yet, the card shows an honest message with a "Continue in
  Demo Mode" fallback, so a live presentation is never blocked.

## Screen 2 — Assistant home
- Free-text box (`DashboardService.handle_utterance`, the same real
  ML → Speech pipeline the technical dashboard uses) plus six quick
  demo buttons: Ask about AI / Robotics / Training, Find a Lab, and an
  Arabic Demo — each supplies a real input string only, never a
  pre-scripted result.
- **Guide** results render the real `GuideService` title/summary/
  sections in a card.
- **Navigation** results render the real `NavigationService` route as a
  vertical chain — *You are here → (real route steps) → destination* —
  built only from `RouteView`/`RouteStep` data actually returned.
- **Speech/fallback** results render the real spoken text; Arabic
  responses (`Language.ARABIC`) are shown right-to-left.
- A small "🤖 …" status pill shows the current real robot action in
  plain language (Waving hello / Speaking / Explaining), sourced from
  `RobotPanelView.last_message` — never a fabricated status.

## What is intentionally not on this screen
The "System Pipeline" indicator and internal per-subsystem status
symbols from the earlier version were removed from this screen. That
information is unchanged and still available on the technical
dashboard (`app/ui/dashboard.py`, `docs/ui_dashboard.md`) for
development/debugging — it was never meant for a professor-facing
demo.

## Robot simulation
All robot actions run on `app.robot.SimulatedRobotBackend` via the
existing `RobotIntegrationAdapter` — identical to the technical
dashboard. No physical hardware is required or claimed; the footer
states this explicitly.

## Error handling
No stack traces are ever shown. Camera, navigation, and guide
failures are shown as short, human-readable messages (e.g. "Camera
access is unavailable.", "I couldn't find a route to that location.").
Technical detail goes to the application logger, not this screen.

## Limitations
- `st.camera_input` shows a continuous live preview but captures one
  still photo per shutter press (with a built-in "Retake photo"
  control) rather than streaming every frame to the detector.
- Best run with the browser and the Streamlit server on the same
  machine, since the camera permission is granted to whichever browser
  opens the app URL.
- DL (gesture) live inference is not wired into this screen, as in the
  prior phase, for the same reason (no camera-driven frame source here).
