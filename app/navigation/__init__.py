"""
Navigation module (SCAFFOLDED, NOT YET IMPLEMENTED).

Owner: Person 1 (AI / Intelligence).

Future responsibility: represent the university map and compute routes
between locations for the robot to (eventually) follow.

Planned flow (not implemented in this phase):

    RouteRequest
          |
          v
    Pathfinding  (app.navigation.pathfinder, over app.navigation.map_data)
          |
          v
    RouteResult

Planned responsibilities:
    - University map representation (locations, connections)
    - Pathfinding between two locations
    - Route generation

Dependency rules (enforced from the first real implementation onward):
    Navigation MUST NOT import app.robot SDK/implementation directly
    Navigation communicates via shared contracts in app.models only

This package currently contains no logic — only file placeholders
(map_data.py, pathfinder.py, service.py) and this docstring. It is NOT
connected to app.robot or app.main in this phase.
"""
