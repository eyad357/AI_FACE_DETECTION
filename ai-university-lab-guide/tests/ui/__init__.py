"""
Test package for app.ui (Route Display presentation layer).

Implemented in this phase. These tests require no camera, no OpenCV,
no Robot, no Robot SDK, no Vision, no Guide network calls, no
database, and no network access — they exercise app.ui in isolation,
using synthetic/plain input data and the existing, stable
app.guide.guide_service.GuideResponse contract only.

Written with unittest.TestCase (Python standard library) rather than
pytest fixtures, so they can be executed with either
`python -m pytest -q` or `python -m unittest discover -s tests/ui` in
environments where pytest is not installed. pytest itself already
appears in requirements.txt and is used by the rest of the test suite;
these tests remain fully pytest-collectible.
"""
