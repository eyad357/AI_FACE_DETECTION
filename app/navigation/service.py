"""
PLACEHOLDER — not implemented in this phase.

This module will expose the public Navigation API once implemented,
e.g.:

    from app.navigation.service import NavigationService

    navigation = NavigationService()
    result = navigation.find_route(request)   # RouteRequest -> RouteResult

Planned responsibility: "How do I get from A to B in the lab/building?"
— nothing more. It will NOT drive the robot itself (that remains
app.robot's / the future orchestration layer's job).

Dependency rules for the future implementation:
    - MUST NOT import app.robot SDK/implementation directly
    - MAY use app.models for any shared result contract
    - MAY use app.config for centralized configuration
    - MAY use app.utils.logger for logging

Not connected to app.robot or app.main in this phase — this file
intentionally contains no executable logic yet.
"""
