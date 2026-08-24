# PHASE_REPORT — Presentation UI: Real Live Camera Fix

## 1. Phase name
Presentation UI Refinement, Part 2 — fixing the real camera preview /
detection UX, and the two environment-dependent test failures from the
previous phase. Builds directly on the prior "Presentation UI
Refinement" phase; no restart, no backend rewrite.

## 2. The bug and its root cause
Reported symptom: pressing the camera button turned on the webcam LED
but no image ever appeared in the page, and the UI never clearly
confirmed a person was actually seen.

Root cause, found by inspecting `app/ui/adapters/vision_adapter.py`
and the previous `app/ui/demo.py`: `VisionAdapter.capture_and_detect()`
opened the camera with `app.vision.camera.Camera` (a server-side
`cv2.VideoCapture`), read one frame, ran detection, and then
**released the camera and discarded the frame** — the captured image
was never passed back to the UI at all, so there was nothing for
Streamlit to display. Separately, `Camera`/`cv2.VideoCapture` opens
the camera on the *machine running the Streamlit server process*, not
necessarily the viewer's browser — reliable only when both are the
same machine, and even then only if the frame is actually rendered.

## 3. Fix
Switched the presentation screen's camera capture mechanism from a
server-side `cv2.VideoCapture` grab to Streamlit's native, zero-new-
dependency `st.camera_input` widget, which renders a **genuine live
viewfinder in the presenter's own browser** (real `getUserMedia`
permission prompt + live preview + shutter button) before any capture
happens — this directly fixes "LED on, no visible feed" because the
preview now lives in the browser itself, not on the server.

The captured photo (JPEG bytes) is decoded with OpenCV and fed
directly into the **same, unmodified, real `FaceDetector`** class
Vision has always used — nothing about face detection was
reimplemented or faked. `app/vision/camera.py` and
`app/vision/face_detector.py` are byte-for-byte unchanged.

New UI-layer (thin, additive) code:
- `VisionAdapter.detect_in_frame(frame)` — new adapter method that
  runs the real `FaceDetector` against an already-captured frame,
  bypassing only `Camera`'s device-open step (the frame already came
  from a real browser capture). `VisionAdapter.capture_and_detect()`
  (the `Camera`-based path used by the technical dashboard) is
  unchanged and still available.
- `DashboardService.analyze_photo(frame)` — thin orchestration
  wrapper around the above, mirroring `refresh_perception()`'s
  session-event recording. Additive; `refresh_perception()` unchanged.
- `PerceptionPanelView.frame` — new **optional** field (default
  `None`) so the raw captured frame can be carried through for display
  if ever needed. Purely additive to a UI-owned dataclass — every
  existing field, every existing caller, and the technical dashboard's
  use of this view model are unaffected.
- `app/ui/demo.py` — Screen 1 rewritten around `st.camera_input`
  (see below).

## 4. Camera states now distinguished on screen
1. **No photo yet** — the live browser viewfinder is shown by the
   widget itself; status pill reads "Looking for you...".
2. **Camera/photo unavailable or unreadable** — an honest message
   ("Camera access is unavailable." / "Could not read the captured
   photo.") with a "Continue in Demo Mode" fallback. Never a crash,
   never a fabricated detection.
3. **No person detected** — "I can't see you yet. Please look toward
   the camera and retake the photo." (the widget's own built-in
   "Retake photo" control triggers a fresh capture).
4. **Person detected** — "✓ Person detected" → **"Welcome! It's great
   to see you."** → real robot GREET/WAVE status shown → "Continue"
   into the assistant.

"Camera opened" and "preview active" are one and the same state under
`st.camera_input` (the widget handles both, showing the live feed the
moment the browser grants permission) — merged into state 1 above
rather than invented as separate, unobservable Python-side states.

## 5. Greeting: exactly once, no loops
Each captured photo's bytes are hashed (`hashlib.md5`) into
`st.session_state["demo_photo_signature"]`. Detection (and, on a
positive detection, the real robot GREET/WAVE call) only runs when
this signature differs from the last one processed — so any Streamlit
rerun triggered by *other* widgets on the page (or simply re-rendering)
never re-runs detection or re-fires the robot for the same capture.
Retaking the photo produces new bytes → a new signature → processed
again, exactly once. Covered by
`TestPhotoProcessing::test_same_capture_is_only_processed_once` and
`::test_a_new_capture_is_processed_again`.

"Continue in Demo Mode" (available at every camera-stage sub-state)
never calls the greeting path — it does not claim a detection that
didn't happen; the assistant home shows a neutral "Hi there!" instead
of "Welcome! It's great to see you." in that case.

## 6. Test suite fixes (from the previous phase's environment bug)
The previous phase's `tests/ui/test_demo.py` had exactly the two
problems reported:
- It asserted `camera_available is False`, which is only true in a
  headless CI box, not on a real machine with a real webcam.
- It clicked a hardcoded button key (`demo_skip`) that didn't match
  the key actually rendered in the state the test put the app in.

Both are structurally impossible now, not just patched: the new camera
path (`st.camera_input`) never touches server-side camera hardware in
the first place, so **no AppTest-level assertion in this suite depends
on whether the test machine has a camera**. The tests that need a
specific detection outcome (person detected / not detected) call the
presentation layer's own `_process_captured_photo()` directly and
**stub the Vision boundary** (`FaceDetector.detect`) with
`monkeypatch`, per the requirement to mock/stub rather than assume an
environment. One test (`test_detect_in_frame_on_a_blank_frame_...`)
exercises the *real* `FaceDetector` against a synthetic blank frame
with zero mocking — deterministically "no face" — to keep at least one
fully real, unmocked path under test.

## 7. Files changed
```
app/ui/demo.py                        Screen 1 rewritten around st.camera_input (live browser preview)
app/ui/adapters/vision_adapter.py     + detect_in_frame() (additive; capture_and_detect() unchanged)
app/ui/dashboard_service.py           + analyze_photo() (additive; refresh_perception() unchanged)
app/ui/dashboard_view_models.py       PerceptionPanelView + optional `frame` field (additive)
tests/ui/test_demo.py                 Camera tests rewritten to be deterministic (mocked Vision boundary); fixed key mismatch
PHASE_REPORT.md                       This report
```
`app/vision/camera.py`, `app/vision/face_detector.py`,
`app/ui/dashboard.py` (technical dashboard), and every non-UI
subsystem (ML, DL, Navigation, Decision, Guide, Speech, Robot, Robot
Integration) are byte-for-byte unchanged. No public contract
(`RobotCommandType`, `RobotController`, `RobotExecutionResult`,
Vision/Decision/Navigation/Guide/Speech contracts) was touched.

## 8. Assistant home / Guide / Navigation / Robot
Unchanged from the previous phase and still real end-to-end: quick
buttons and free text go through `DashboardService.handle_utterance`
(real ML → Speech), `get_guide_content` (real Guide), `request_route`
(real Navigation), and `robot_action` (real
`RobotIntegrationAdapter` → `SimulatedRobotBackend`). Results render
in the same clean cards (Guide card, "You are here → … → destination"
navigation chain, RTL for Arabic).

## 9. Test results
- Focused: `tests/ui/test_demo.py` — **23 passed** (was 16; +7 net —
  6 new deterministic camera/photo-pipeline tests, 1 net test-name
  change fixing the environment-dependent one), 0 failed.
- Full suite: **754 passed, 2 skipped** (previous phase: 747 passed, 2
  skipped). Zero regressions, zero removed/weakened assertions.
- Launched `streamlit run app/ui/demo.py` (headless, port probe):
  server starts cleanly, responds HTTP 200, no exceptions in logs.
  `AppTest` confirms a `camera_input` element renders on first load and
  the full camera → (stub) detection → greeting → assistant → Guide /
  Navigation → restart flow all execute without exception.
- **Honesty note on live verification**: this sandbox has no physical
  webcam or browser, so the actual browser permission prompt / live
  video feed / in-person face capture could not be visually verified
  here. What *is* verified: the widget renders, the decode → real
  `FaceDetector` → real `Decision`/`Robot` pipeline behaves correctly
  for both detected and not-detected outcomes, and the previous
  "LED-on-but-no-image" root cause (a discarded frame, never rendered)
  is structurally gone because the preview now lives in
  `st.camera_input` itself, not in a discarded server-side buffer.

## 10. Launch command
```
python -m streamlit run app/ui/demo.py
```
Technical dashboard (unchanged, still available):
```
python -m streamlit run app/ui/dashboard.py
```

## 11. Known limitations
- `st.camera_input` captures a single photo per press (with a built-in
  "Retake photo" control), not a continuously streamed video frame —
  this is Streamlit's standard live-camera mechanism and matches the
  project's existing single-frame-per-detection design (`Camera.open()
  /read()/release()` was already per-call, not streaming).
  The **live viewfinder itself** (before the shutter press) is
  continuous browser video — only the analyzed photo is a snapshot.
- Runs best when the browser and the Streamlit server are on the same
  machine (a local `streamlit run` for the live demo), since the
  camera permission prompt is served to whichever browser opens the
  app URL.
- DL (gesture) live inference remains out of scope for this screen, as
  in prior phases (no camera-driven frame source wired to DL here).

## 12. Final verdict
The reported failure mode (webcam LED on, nothing visible, no honest
detection feedback) is fixed at its root cause: the live preview now
renders in the browser via Streamlit's native camera widget, and the
same real `FaceDetector` runs against the actual captured photo, with
detection state, greeting, and the transition to the assistant home
all clearly distinguished on screen and backed by real service calls.
Both previously-reported test failures are fixed by construction
(hardware-independent capture path) rather than patched over, and the
full suite is green with no regressions.
