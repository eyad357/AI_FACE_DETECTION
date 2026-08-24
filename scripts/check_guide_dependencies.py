"""
Standalone dependency-validation script (not part of the app or test
suite -- run manually / in CI to verify app.guide's import boundaries).

Verifies, via AST inspection of every .py file under app/guide/:
    - Guide imports app.models, app.config, app.utils, and its own
      submodules freely.
    - Guide imports EXACTLY ONE symbol from app.decision:
      app.decision.event_manager.GuideTopic -- a plain, stable topic
      identifier enum, not application behavior. This is a documented,
      pre-existing architectural exception (see docs/guide.md,
      "Navigation vs Guide boundary" / "the Decision exception", and
      docs/integration_contract.md), predating this phase, that this
      phase's blanket "no Decision dependency" instruction conflicts
      with. Per this phase's own "use the existing contract, don't
      duplicate it, don't redesign the existing architecture" rules,
      the existing exception is preserved rather than removed.
    - Guide MUST NOT import app.decision.state_manager (Decision's
      state machine / behavior), nor app.ml, app.dl, app.vision,
      app.navigation, app.robot, app.ui, or app.main.
    - No circular imports (app.models does not import app.guide;
      app.config does not import app.guide).

Usage:
    python scripts/check_guide_dependencies.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = REPO_ROOT / "app"

FORBIDDEN_FOR_GUIDE = {
    "app.ml",
    "app.dl",
    "app.vision",
    "app.navigation",
    "app.robot",
    "app.ui",
    "app.main",
}

# Decision is forbidden EXCEPT for this one documented, pre-existing
# symbol -- see module docstring.
FORBIDDEN_DECISION_SUBMODULES = {
    "app.decision.state_manager",
}
ALLOWED_DECISION_IMPORT = "app.decision.event_manager"  # GuideTopic only

ALLOWED_APP_INTERNAL_FOR_GUIDE = {
    "app.models",
    "app.config",
    "app.utils",
    "app.guide",  # Guide may import its own submodules
}


def _imports_in_file(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name, None))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names = [alias.name for alias in node.names]
                results.append((node.module, names))
    return results


def _is_forbidden(module: str) -> str | None:
    for forbidden in FORBIDDEN_FOR_GUIDE:
        if module == forbidden or module.startswith(forbidden + "."):
            return forbidden
    return None


def _is_app_internal(module: str) -> bool:
    return module == "app" or module.startswith("app.")


def check_guide_dependencies() -> list[str]:
    violations = []
    guide_dir = APP_ROOT / "guide"
    for py_file in sorted(guide_dir.rglob("*.py")):
        rel = py_file.relative_to(REPO_ROOT)
        for module, names in _imports_in_file(py_file):
            if not _is_app_internal(module):
                continue  # third-party / stdlib, not our concern here

            forbidden = _is_forbidden(module)
            if forbidden:
                violations.append(
                    f"{rel}: forbidden import of {module!r} "
                    f"(matches forbidden root {forbidden!r})"
                )
                continue

            if module.startswith("app.decision"):
                if module in FORBIDDEN_DECISION_SUBMODULES:
                    violations.append(
                        f"{rel}: forbidden import of {module!r} "
                        "(Decision's state machine is off-limits to Guide)"
                    )
                elif module == ALLOWED_DECISION_IMPORT:
                    if names is not None and any(n != "GuideTopic" for n in names):
                        violations.append(
                            f"{rel}: imports {names!r} from {module!r}; only "
                            "GuideTopic is an approved exception"
                        )
                else:
                    violations.append(
                        f"{rel}: unexpected import from app.decision: {module!r} "
                        f"(only {ALLOWED_DECISION_IMPORT}.GuideTopic is approved)"
                    )
                continue

            allowed = any(
                module == a or module.startswith(a + ".")
                for a in ALLOWED_APP_INTERNAL_FOR_GUIDE
            )
            if not allowed:
                violations.append(
                    f"{rel}: unexpected app-internal import {module!r} "
                    f"(not in allowed set {sorted(ALLOWED_APP_INTERNAL_FOR_GUIDE)})"
                )
    return violations


def check_no_circular_import() -> list[str]:
    """app.models and app.config must not import app.guide (would create a cycle)."""
    violations = []
    for rel_path in ["app/models/schemas.py", "app/models/__init__.py", "app/config.py"]:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        for module, _names in _imports_in_file(path):
            if module == "app.guide" or module.startswith("app.guide."):
                violations.append(f"{rel_path}: imports app.guide -- circular dependency")
    return violations


def main() -> int:
    violations = check_guide_dependencies() + check_no_circular_import()
    if violations:
        print("DEPENDENCY VALIDATION FAILED:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("Dependency validation PASSED:")
    print("  - app.guide imports only app.models / app.config / app.utils /")
    print("    app.guide.* / app.decision.event_manager.GuideTopic (single")
    print("    documented exception)")
    print("  - app.guide does not import app.decision.state_manager, app.ml,")
    print("    app.dl, app.vision, app.navigation, app.robot, app.ui, or app.main")
    print("  - no circular imports (app.models / app.config do not import")
    print("    app.guide)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
