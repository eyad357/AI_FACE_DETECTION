"""
Dependency-isolation audit for app.navigation.

Statically parses every source file under app/navigation/ with the
`ast` module (rather than importing them) and asserts none of them
import a forbidden module, per docs/navigation.md and the Person 1
Navigation task's dependency-isolation rules.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

NAVIGATION_PACKAGE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "app" / "navigation"
)

FORBIDDEN_MODULE_PREFIXES = (
    "app.vision",
    "app.ml",
    "app.dl",
    "app.speech",
    "app.decision",
    "app.main",
    "app.ui",
    "app.robot.robot_controller",
)


def _navigation_source_files():
    return sorted(NAVIGATION_PACKAGE_DIR.glob("*.py"))


def _imported_module_names(file_path: Path):
    tree = ast.parse(file_path.read_text(), filename=str(file_path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


class TestNoForbiddenImports:
    @pytest.mark.parametrize("file_path", _navigation_source_files(), ids=lambda p: p.name)
    def test_file_has_no_forbidden_imports(self, file_path):
        imported = _imported_module_names(file_path)
        for module_name in imported:
            for forbidden in FORBIDDEN_MODULE_PREFIXES:
                assert not (
                    module_name == forbidden or module_name.startswith(forbidden + ".")
                ), (
                    f"{file_path.name} imports forbidden module "
                    f"{module_name!r} (matches forbidden prefix {forbidden!r})"
                )

    def test_navigation_package_has_source_files(self):
        # Guard against this audit silently passing because the glob
        # found nothing (e.g. a path typo).
        assert len(_navigation_source_files()) >= 4


class TestNoDirectRobotOrMainImport:
    def test_no_module_imports_app_robot_controller_directly(self):
        for file_path in _navigation_source_files():
            imported = _imported_module_names(file_path)
            assert "app.robot.robot_controller" not in imported
            assert "app.main" not in imported

    def test_app_robot_package_itself_is_allowed_absence(self):
        # Navigation must not import app.robot's *implementation*
        # (robot_controller). It also does not need bare `app.robot`
        # for anything in this phase, so this test just documents that
        # no navigation module currently imports app.robot at all.
        for file_path in _navigation_source_files():
            imported = _imported_module_names(file_path)
            assert "app.robot" not in imported
