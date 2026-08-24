"""
Context — combined-request planning module.

Owner: Person 1 (AI / Intelligence).

Responsibility: given an already-classified IntentResult (from
app.ml), determine which capabilities (Navigation, Guide, both, or
neither) are required to fulfill the request. Nothing more.

Flow:

    IntentResult                       (app.models.schemas, from app.ml)
          |
          v
    ContextService.plan()               (app.context.service)
          |
          v
    RequestPlan                         (app.models.schemas)

For COMBINED requests, a future orchestration layer (app.main) will
call both Navigation and Guide independently and assemble their
results into a CombinedResponse (app.models.schemas) -- app.context
defines that contract's shape but never constructs a populated
instance itself, since doing so would require calling Navigation and
Guide, which app.context is explicitly forbidden from doing.

Context is NOT responsible for:
    - classifying student text (app.ml)
    - calculating routes (app.navigation)
    - looking up information (app.guide)
    - robot control or speech (app.robot)
    - gesture recognition (app.dl)
    - face detection (app.vision)
    - final application orchestration (app.main)

Dependency rules (enforced -- see docs/context.md):
    Context MUST NOT import app.ml, app.dl, app.vision, app.navigation,
    app.guide, app.robot, app.ui, or app.main.
    Context communicates via shared contracts in app.models only.

This package contains:
    service.py   public API (ContextService)

Context does NOT perform integration: it is not wired into app.main,
app.decision, app.navigation, or app.guide in this phase. That remains
a future integration phase -- see docs/context.md, "Future integration
boundary".
"""
