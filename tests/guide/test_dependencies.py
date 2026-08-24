"""
Dependency-isolation tests for app.guide.

Complements tests/test_guide.py's existing checks (no app.robot,
app.vision, or app.decision.state_manager import) with the additional
forbidden modules specific to P1-GUIDE: app.ml, app.dl, app.navigation,
app.ui, and app.main. Also asserts the single documented exception --
app.decision.event_manager.GuideTopic -- is exactly what's imported
from app.decision, nothing broader.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

GUIDE_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "guide"

FORBIDDEN_ROOTS = (
    "app.ml",
    "app.dl",
    "app.vision",
    "app.navigation",
    "app.robot",
    "app.ui",
    "app.main",
)
FORBIDDEN_DECISION_SUBMODULES = ("app.decision.state_manager",)
ALLOWED_DECISION_MODULE = "app.decision.event_manager"


def _imports_in_file(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name, None))
        elif isinstance(node, ast.ImportFrom) and node.module:
            results.append((node.module, [a.name for a in node.names]))
    return results


def _guide_py_files():
    return sorted(GUIDE_DIR.rglob("*.py"))


class TestNoForbiddenDependencies:
    @pytest.mark.parametrize("py_file", _guide_py_files(), ids=lambda p: p.name)
    def test_no_forbidden_root_imports(self, py_file):
        violations = []
        for module, _names in _imports_in_file(py_file):
            for forbidden in FORBIDDEN_ROOTS:
                if module == forbidden or module.startswith(forbidden + "."):
                    violations.append(module)
        assert violations == [], f"{py_file.name} imports forbidden module(s): {violations}"

    @pytest.mark.parametrize("py_file", _guide_py_files(), ids=lambda p: p.name)
    def test_no_decision_state_manager_import(self, py_file):
        violations = []
        for module, _names in _imports_in_file(py_file):
            if module in FORBIDDEN_DECISION_SUBMODULES:
                violations.append(module)
        assert violations == [], f"{py_file.name} imports Decision's state machine: {violations}"

    def test_decision_import_is_limited_to_guide_topic(self):
        """
        The one approved exception: app.decision.event_manager.GuideTopic
        (a plain, stable topic identifier), and nothing else from
        app.decision. See docs/guide.md, "Navigation vs Guide boundary".
        """
        for py_file in _guide_py_files():
            for module, names in _imports_in_file(py_file):
                if not module.startswith("app.decision"):
                    continue
                assert module == ALLOWED_DECISION_MODULE, (
                    f"{py_file.name} imports from unexpected Decision module "
                    f"{module!r}"
                )
                if names is not None:
                    assert names == ["GuideTopic"], (
                        f"{py_file.name} imports {names!r} from {module!r}; "
                        "only GuideTopic is approved"
                    )

    def test_no_circular_import_from_models_or_config(self):
        repo_root = GUIDE_DIR.parent.parent
        for rel_path in ["app/models/schemas.py", "app/models/__init__.py", "app/config.py"]:
            path = repo_root / rel_path
            if not path.exists():
                continue
            for module, _names in _imports_in_file(path):
                assert not (module == "app.guide" or module.startswith("app.guide.")), (
                    f"{rel_path} imports app.guide -- circular dependency"
                )
