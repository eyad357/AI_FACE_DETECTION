"""Dependency-isolation tests for app.context."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

CONTEXT_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "context"

FORBIDDEN_ROOTS = (
    "app.ml",
    "app.dl",
    "app.vision",
    "app.navigation",
    "app.guide",
    "app.robot",
    "app.ui",
    "app.main",
)


def _imports_in_file(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            results.append(node.module)
    return results


def _context_py_files():
    return sorted(CONTEXT_DIR.rglob("*.py"))


class TestNoForbiddenDependencies:
    @pytest.mark.parametrize("py_file", _context_py_files(), ids=lambda p: p.name)
    def test_no_forbidden_root_imports(self, py_file):
        violations = []
        for module in _imports_in_file(py_file):
            for forbidden in FORBIDDEN_ROOTS:
                if module == forbidden or module.startswith(forbidden + "."):
                    violations.append(module)
        assert violations == [], f"{py_file.name} imports forbidden module(s): {violations}"

    def test_no_ml_dependency(self):
        for py_file in _context_py_files():
            assert not any(
                m == "app.ml" or m.startswith("app.ml.")
                for m in _imports_in_file(py_file)
            )

    def test_no_dl_dependency(self):
        for py_file in _context_py_files():
            assert not any(
                m == "app.dl" or m.startswith("app.dl.")
                for m in _imports_in_file(py_file)
            )

    def test_no_vision_dependency(self):
        for py_file in _context_py_files():
            assert not any(
                m == "app.vision" or m.startswith("app.vision.")
                for m in _imports_in_file(py_file)
            )

    def test_no_navigation_dependency(self):
        for py_file in _context_py_files():
            assert not any(
                m == "app.navigation" or m.startswith("app.navigation.")
                for m in _imports_in_file(py_file)
            )

    def test_no_guide_dependency(self):
        for py_file in _context_py_files():
            assert not any(
                m == "app.guide" or m.startswith("app.guide.")
                for m in _imports_in_file(py_file)
            )

    def test_no_robot_dependency(self):
        for py_file in _context_py_files():
            assert not any(
                m == "app.robot" or m.startswith("app.robot.")
                for m in _imports_in_file(py_file)
            )

    def test_no_main_dependency(self):
        for py_file in _context_py_files():
            assert not any(
                m == "app.main" for m in _imports_in_file(py_file)
            )

    def test_no_circular_import_from_models_or_config(self):
        repo_root = CONTEXT_DIR.parent.parent
        for rel_path in ["app/models/schemas.py", "app/models/__init__.py", "app/config.py"]:
            path = repo_root / rel_path
            if not path.exists():
                continue
            for module in _imports_in_file(path):
                assert not (module == "app.context" or module.startswith("app.context.")), (
                    f"{rel_path} imports app.context -- circular dependency"
                )


class TestNoTextClassificationCode:
    """
    Static guardrail: Context must consume IntentResult only, never
    perform its own classification (TF-IDF, model loading, keyword
    matching over raw text).
    """

    FORBIDDEN_IDENTIFIERS = (
        "TfidfVectorizer",
        "LogisticRegression",
        "sklearn",
        "joblib",
    )

    def test_no_ml_library_references(self):
        for py_file in _context_py_files():
            text = py_file.read_text(encoding="utf-8")
            for identifier in self.FORBIDDEN_IDENTIFIERS:
                assert identifier not in text, f"{py_file.name} references {identifier!r}"
