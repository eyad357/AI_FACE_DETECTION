"""
Standalone dependency-validation script (not part of the app or test
suite -- run manually / in CI to verify app.dl's import boundaries).

Verifies, via AST inspection of every .py file under app/dl/:
    - DL imports app.models (allowed) and nothing else app-internal
      except app.config and app.utils.logger (both pre-existing,
      cross-cutting infrastructure used by every module in this repo).
    - DL never imports app.ml, app.vision, app.robot, app.decision,
      app.guide, app.navigation, app.ui, or app.main.
    - No circular imports are introduced (app.models does not import
      app.dl; app.config does not import app.dl).

Usage:
    python scripts/check_dl_dependencies.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = REPO_ROOT / "app"

FORBIDDEN_FOR_DL = {
    "app.ml",
    "app.vision",
    "app.robot",
    "app.decision",
    "app.guide",
    "app.navigation",
    "app.ui",
    "app.main",
}

ALLOWED_APP_INTERNAL_FOR_DL = {
    "app.models",
    "app.config",
    "app.utils",
    "app.dl",  # DL may import its own submodules
}


def _imports_in_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _is_forbidden(module: str) -> str | None:
    for forbidden in FORBIDDEN_FOR_DL:
        if module == forbidden or module.startswith(forbidden + "."):
            return forbidden
    return None


def _is_app_internal(module: str) -> bool:
    return module == "app" or module.startswith("app.")


def check_dl_dependencies() -> list[str]:
    violations = []
    dl_dir = APP_ROOT / "dl"
    for py_file in sorted(dl_dir.rglob("*.py")):
        rel = py_file.relative_to(REPO_ROOT)
        for module in _imports_in_file(py_file):
            if not _is_app_internal(module):
                continue  # third-party / stdlib, not our concern here
            forbidden = _is_forbidden(module)
            if forbidden:
                violations.append(
                    f"{rel}: forbidden import of {module!r} "
                    f"(matches forbidden root {forbidden!r})"
                )
                continue
            allowed = any(
                module == a or module.startswith(a + ".")
                for a in ALLOWED_APP_INTERNAL_FOR_DL
            )
            if not allowed:
                violations.append(
                    f"{rel}: unexpected app-internal import {module!r} "
                    f"(not in allowed set {sorted(ALLOWED_APP_INTERNAL_FOR_DL)})"
                )
    return violations


def check_no_circular_import() -> list[str]:
    """app.models and app.config must not import app.dl (would create a cycle)."""
    violations = []
    for rel_path in ["app/models/schemas.py", "app/models/__init__.py", "app/config.py"]:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        for module in _imports_in_file(path):
            if module == "app.dl" or module.startswith("app.dl."):
                violations.append(f"{rel_path}: imports app.dl -- circular dependency")
    return violations


def check_no_ml_dependency() -> list[str]:
    """Explicit, redundant check: DL must never import the locked app.ml module."""
    violations = []
    dl_dir = APP_ROOT / "dl"
    for py_file in sorted(dl_dir.rglob("*.py")):
        for module in _imports_in_file(py_file):
            if module == "app.ml" or module.startswith("app.ml."):
                violations.append(f"{py_file.relative_to(REPO_ROOT)}: imports app.ml")
    return violations


def main() -> int:
    violations = (
        check_dl_dependencies() + check_no_circular_import() + check_no_ml_dependency()
    )
    if violations:
        print("DEPENDENCY VALIDATION FAILED:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("Dependency validation PASSED:")
    print("  - app.dl imports only app.models / app.config / app.utils / app.dl.*")
    print("  - app.dl does not import app.ml, app.vision, app.robot, app.decision,")
    print("    app.guide, app.navigation, app.ui, or app.main")
    print("  - no circular imports (app.models / app.config do not import app.dl)")
    print("  - app.dl -> app.ml forbidden dependency: confirmed absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
