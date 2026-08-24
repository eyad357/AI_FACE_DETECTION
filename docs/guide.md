# Guide Module

Guide answers **"what information should be provided?"** It is a
content + service layer, not an orchestrator, and not a decision-maker.

Guide does **not**:
- decide whether a visitor exists, or manage application state (Decision's job)
- classify intent (the future `app.ml`'s job)
- calculate routes or distances (the future `app.navigation`'s job)
- control the Robot or perform speech synthesis (Robot's job)
- render UI (UI's job)
- orchestrate the application (`app.main`'s job)

Guide has **two independent, parallel flows**, both reachable through
the same `GuideService`:

```
GuideService
├── get_topic_content(topic: GuideTopic)      -- existing, unchanged since Phase 3
└── get_location_info(location_id: str)       -- new, added in Phase G1
```

Both return the same `GuideResponse` type. Neither flow knows about the
other — they simply share a service class and a response contract.

## 1. The existing topic flow (unchanged)

`GuideTopic` (`app.decision.event_manager.GuideTopic`) is a small, fixed
Enum with 4 members: `AI_PROJECTS`, `ROBOTICS`, `TRAINING`,
`LAB_INFORMATION`. It represents **lab-tour categories** for the
original "AI University Lab Guide Robot" concept, and is reused as-is
from Decision's event vocabulary — Guide never defines a second copy.

```python
from app.guide import GuideService
from app.decision.event_manager import GuideTopic

response = GuideService().get_topic_content(GuideTopic.AI_PROJECTS)
```

This flow is already wired into the live Decision → `app.main` → Robot
pipeline (an `EXPLANATION_REQUIRED` `DecisionEvent` carries a topic,
`app.main` calls `get_topic_content()`, and the result's `spoken_text`
becomes a `RobotCommand(EXPLAIN_AI, ...)`). **Nothing about this flow
changed in Phase G1** — same content, same behavior, same tests, all
still passing.

## 2. The new location flow (Phase G1)

As the project grew into an "AI University Assistant & Navigator
Robot," a second kind of request emerged: *"tell me about place X"* /
*"what can I do at place X"* — about real, open-ended university
**locations**, not fixed lab-tour categories. Forcing that into
`GuideTopic` would mean growing a supposedly-stable shared Enum (and,
transitively, `RobotCommandType` and `app.main`'s topic→command
mapping) every time a new building or office is added — which doesn't
scale and isn't necessary.

Instead, `app.guide.locations` introduces a second, independent
identifier:

```python
LocationId = str   # e.g. "ai_lab", "library" -- not an Enum
```

Adding a location is a **pure data change** — add an entry to
`LOCATION_CONTENT`, no code change to `GuideService` required.

```python
from app.guide import GuideService

response = GuideService().get_location_info("ai_lab")
```

### `LocationRecord`

```python
@dataclass(frozen=True)
class LocationRecord:
    location_id: str
    name: str
    building: str
    floor: Optional[str]
    description: str
    services: List[str]
    facilities: List[str]
    opening_info: Optional[str]
    spoken_text: str
```

### Guide vs. Navigation — field ownership

| Guide owns (informational) | Navigation owns (future, not implemented) |
|---|---|
| `name`, `description` | coordinates / position |
| `services`, `facilities` | waypoints, route graph |
| `building`, `floor` | distance |
| `opening_info` | turn-by-turn directions |
| `spoken_text` | |

The only thing the two sides are expected to eventually share is the
`location_id` string itself, used as a join key by a future
orchestration layer — Guide does not need Navigation to exist, and
Navigation (once built) will not need to import Guide.

`LocationRecord` deliberately has **no** coordinate/route/distance
fields — enforced by `tests/test_guide.py::TestLocationDataConsistency::test_location_content_has_no_navigation_fields`.

## 3. `GuideResponse` — one contract, both flows

```python
@dataclass(frozen=True)
class GuideResponse:
    topic: Optional[GuideTopic]       # set only by get_topic_content()
    title: str
    summary: str
    sections: List[str] = []
    spoken_text: str = ""
    timestamp: datetime
    location_id: Optional[str] = None # set only by get_location_info()  [NEW in G1]
```

`location_id` was added **additively**, with a default of `None` — the
existing `topic` field, all existing fields, and every existing
construction of `GuideResponse` (in code and in tests) are completely
unaffected. A topic-based response always has `location_id=None`; a
location-based response always has `topic=None`.

`GuideResponse` still lives in `app/guide/guide_service.py`, not
`app/models/schemas.py` — unchanged rationale from Phase 3: it avoids
an `app.models → app.decision` dependency, and mirrors the same
pattern already used for `DecisionEvent`.

## 4. Prototype data disclaimer

All content in `app.guide.content` (topics) and `app.guide.locations`
(locations) is **prototype / example data** for this project. Building
names, floors, services, and opening-hours-style text do **not**
represent any real university's actual facilities and should be
replaced with real institutional data when available — without any
change to `GuideService`'s logic, since all of it is centralized in
`TOPIC_CONTENT` / `LOCATION_CONTENT` data dictionaries.

The current prototype locations: AI Lab, Robotics Lab, Computer Lab,
University Library, Engineering Building, Student Affairs, Main
Auditorium, Innovation Lab, Lecture Rooms, Cafeteria.

## 5. Future integration boundary (not implemented yet)

Guide is **not** wired into Decision or `app.main` for the location
flow yet (that is deliberately deferred — see the roadmap below).
`get_location_info()` is fully usable and tested standalone today; a
future phase will decide how a `DecisionEvent` carries a `location_id`
and how `app.main` reaches Guide for it, exactly mirroring the existing
`EXPLANATION_REQUIRED` → `get_topic_content()` pattern already in
production.

```
Future (not yet implemented):

Student question → ML → IntentResult(intent, location_id)
    → Decision → a future DecisionEventType carrying location_id
    → app.main → GuideService.get_location_info(location_id)
    → GuideResponse → app.main → RobotCommand(SPEAK, text=spoken_text)

For a COMBINED request ("where is X and what can I do there"):
    → app.main also calls a future NavigationService for the route
    → Guide's contribution is only the information half; it never
      produces or reasons about route content
```

Guide will never import `app.ml`, `app.dl`, `app.navigation`, or
`app.main` to make this work — the future orchestration layer calls
*into* Guide, not the other way around, exactly like the existing
Robot/Decision boundaries.

## 6. Dependency guarantees (all test-enforced)

Guide imports only: Python standard library, the single `GuideTopic`
symbol from `app.decision.event_manager`, and its own submodules
(`app.guide.content`, `app.guide.locations`). It never imports
`app.robot`, `app.vision`, `app.decision.state_manager`, `app.ml`,
`app.dl`, `app.navigation`, or `app.main`. `app.guide.locations`
specifically has **zero** app-internal imports at all.

See [`docs/integration_contract.md`](integration_contract.md) for the
project-wide dependency direction table.
