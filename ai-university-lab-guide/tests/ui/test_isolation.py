"""
Import-isolation tests for app.ui.

Verifies:
    - app.ui and its submodules import cleanly with no hardware,
      camera, or network access.
    - app.ui (and each of its submodules) does not import any
      protected/other-workstream module: app.robot, app.vision,
      app.ml, app.dl, app.main. app.navigation is checked separately,
      since Navigation is still an unimplemented placeholder in this
      phase (see PHASE_REPORT.md) and app.ui does not depend on it.

This is done via static source inspection (compile + AST), not by
importing the forbidden modules ourselves, so the test does not
accidentally require optional heavy dependencies (e.g. OpenCV) that
app.vision needs but app.ui must not.
"""

import ast
import importlib
import unittest
from pathlib import Path

import app.ui

_UI_PACKAGE_DIR = Path(app.ui.__file__).parent

_FORBIDDEN_MODULE_PREFIXES = (
    "app.robot",
    "app.vision",
    "app.ml",
    "app.dl",
    "app.main",
    "app.navigation",
)


def _imported_module_names(py_file: Path):
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


class TestUiModuleIsolation(unittest.TestCase):
    def test_ui_package_imports_without_error(self):
        importlib.import_module("app.ui")

    def test_ui_submodules_import_without_error(self):
        for name in ("view_models", "route_display", "renderer", "guide_ui"):
            importlib.import_module(f"app.ui.{name}")

    def test_no_ui_source_file_imports_a_protected_module(self):
        py_files = sorted(_UI_PACKAGE_DIR.glob("*.py"))
        self.assertTrue(py_files, "expected app/ui/*.py files to exist")

        violations = []
        for py_file in py_files:
            for imported in _imported_module_names(py_file):
                if any(
                    imported == prefix or imported.startswith(prefix + ".")
                    for prefix in _FORBIDDEN_MODULE_PREFIXES
                ):
                    violations.append((py_file.name, imported))

        self.assertEqual(
            violations,
            [],
            f"app/ui files must not import protected modules: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
