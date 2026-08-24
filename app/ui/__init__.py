"""
Route Display presentation layer (Person 2 — UI).

Responsibility: adapt already-decided domain data (a GuideResponse,
route/navigation data, system status) into display-ready view models
(app.ui.view_models) and render them (app.ui.renderer). This package
performs no route calculation, no pathfinding, and no intent
classification -- it only shapes and displays whatever it is given.

See tests/ui/test_isolation.py for the enforced dependency rules and
docs/integration_contract.md for the full picture.
"""
