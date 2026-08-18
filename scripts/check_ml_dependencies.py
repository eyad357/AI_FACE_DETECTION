"""
Standalone dependency-validation script (not part of the app or test
suite -- run manually / in CI to verify app.ml's import boundaries).

Verifies, via AST inspection of every .py file under app/ml/:
    - ML imports app.models (allowed) and nothing else app-internal
      except app.config and app.utils.logger (both pre-existing,
      cross-cutting infrastructure used by every module in this repo).
    - ML never imports app.vision, app.robot, app.decision, app.guide,
      app.navigation, app.dl, app.ui, or app.main.
    - No circular imports are introduced (app.models does not import
      app.ml; app.config does not import app.ml).

Usage:
    python check_ml_dependencies.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = REPO_ROOT / "app"

FORBIDDEN_FOR_ML = {
    "app.vision",
    "app.robot",
    "app.decision",
    "app.guide",
    "app.navigation",
    "app.dl",
    "app.ui",
    "app.main",
}

ALLOWED_APP_INTERNAL_FOR_ML = {
    "app.models",
    "app.config",
    "app.utils",
    "app.ml",  # ML may import its own submodules
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
    for forbidden in FORBIDDEN_FOR_ML:
        if module == forbidden or module.startswith(forbidden + "."):
            return forbidden
    return None


def _is_app_internal(module: str) -> bool:
    return module == "app" or module.startswith("app.")


def check_ml_dependencies() -> list[str]:
    violations = []
    ml_dir = APP_ROOT / "ml"
    for py_file in sorted(ml_dir.rglob("*.py")):
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
                for a in ALLOWED_APP_INTERNAL_FOR_ML
            )
            if not allowed:
                violations.append(
                    f"{rel}: unexpected app-internal import {module!r} "
                    f"(not in allowed set {sorted(ALLOWED_APP_INTERNAL_FOR_ML)})"
                )
    return violations


def check_no_circular_import() -> list[str]:
    """app.models and app.config must not import app.ml (would create a cycle)."""
    violations = []
    for rel_path in ["app/models/schemas.py", "app/models/__init__.py", "app/config.py"]:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        for module in _imports_in_file(path):
            if module == "app.ml" or module.startswith("app.ml."):
                violations.append(f"{rel_path}: imports app.ml -- circular dependency")
    return violations


def main() -> int:
    violations = check_ml_dependencies() + check_no_circular_import()
    if violations:
        print("DEPENDENCY VALIDATION FAILED:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("Dependency validation PASSED:")
    print("  - app.ml imports only app.models / app.config / app.utils / app.ml.*")
    print("  - app.ml does not import app.vision, app.robot, app.decision,")
    print("    app.guide, app.navigation, app.dl, app.ui, or app.main")
    print("  - no circular imports (app.models / app.config do not import app.ml)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
