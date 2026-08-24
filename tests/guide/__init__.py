"""
Test package for app.guide -- the university guide/information module.

These are SUPPLEMENTARY to the pre-existing tests/test_guide.py, which
already covers per-topic content retrieval, unknown-topic handling, the
GuideResponse shape, and Guide's independence from Robot/Vision/
Decision's state machine (part of the protected Phase 7 baseline --
not modified or duplicated here). This package adds the additional
checks P1-GUIDE specifically calls for that didn't exist when
tests/test_guide.py was written: a comprehensive AST-based check
against every module forbidden in THIS phase (app.ml, app.dl,
app.navigation, in addition to the already-tested app.robot/
app.vision), plus determinism, data-integrity, and public-API-surface
checks.
"""
