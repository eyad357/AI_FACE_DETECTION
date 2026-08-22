"""
UI / Route Display layer (Person 2 — Robotics / Interaction).

Responsibility: present guide content, route/navigation information,
and overall system status to a human-facing screen/interface, via
stable, already-decided data (app.guide.guide_service.GuideResponse
and this package's own view models) rather than by depending on
app.vision, app.robot, app.ml, app.dl, app.navigation, app.decision,
or app.main internals directly.

Submodules:
    app.ui.view_models   — display-ready data structures (SystemStatus,
                            GuideContentView, RouteView, etc.).
    app.ui.route_display — adapters from domain contracts (e.g.
                            GuideResponse) into view models.
    app.ui.renderer       — renders view models as text (TextRenderer);
                            a future renderer may target a different
                            output surface without changing view models.
    app.ui.guide_ui       — re-exports the guide-content adapter under
                            its original Phase 1 name for callers that
                            import app.ui.guide_ui directly.

This package must not import app.vision, app.robot, app.ml, app.dl,
app.navigation, or app.main. See docs/contracts.md and
tests/ui/test_isolation.py for the enforced dependency rules.
"""
