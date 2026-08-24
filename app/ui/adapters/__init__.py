"""
Dashboard adapters.

Each adapter is a thin translation boundary between one existing
application service/contract and the dashboard's view models
(app.ui.dashboard_view_models). Adapters never invent data, never
duplicate domain contracts, and never bypass an existing module's
public API. If a real value cannot be obtained, an adapter reports an
honest unavailable/degraded state instead of fabricating one.
"""
