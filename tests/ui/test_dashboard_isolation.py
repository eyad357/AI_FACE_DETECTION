"""
Static architecture audit for the dashboard layer (Section 10 of the
UI Dashboard phase instructions).

Verifies, via AST inspection of the actual source files:
    - the dashboard does not import app.main unnecessarily
    - the dashboard does not duplicate domain contracts
      (RobotCommandType, GuideTopic, RouteResult) by redefining them
    - dashboard modules import successfully with no circular import
      errors
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

_DASHBOARD_FILES = [
    Path("app/ui/dashboard.py"),
    Path("app/ui/dashboard_service.py"),
    Path("app/ui/dashboard_view_models.py"),
    Path("app/ui/adapters/vision_adapter.py"),
    Path("app/ui/adapters/ml_adapter.py"),
    Path("app/ui/adapters/dl_adapter.py"),
    Path("app/ui/adapters/decision_adapter.py"),
    Path("app/ui/adapters/guide_adapter.py"),
    Path("app/ui/adapters/navigation_adapter.py"),
    Path("app/ui/adapters/speech_adapter.py"),
    Path("app/ui/adapters/robot_adapter.py"),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _imported_module_names(source: str):
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _defined_class_names(source: str):
    tree = ast.parse(source)
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


class TestNoUnnecessaryMainDependency:
    @pytest.mark.parametrize("relpath", _DASHBOARD_FILES, ids=lambda p: p.name)
    def test_module_does_not_import_app_main(self, relpath):
        path = _repo_root() / relpath
        source = path.read_text(encoding="utf-8")
        imported = _imported_module_names(source)
        assert not any(
            name == "app.main" or name.startswith("app.main.") for name in imported
        ), f"{relpath} imports app.main, which the dashboard should avoid"


class TestNoDuplicatedDomainContracts:
    _FORBIDDEN_CLASS_NAMES = {
        "RobotCommandType",
        "GuideTopic",
        "RouteResult",
        "RouteRequest",
        "DetectionResult",
        "IntentResult",
        "ConversationResponse",
    }

    @pytest.mark.parametrize("relpath", _DASHBOARD_FILES, ids=lambda p: p.name)
    def test_module_does_not_redefine_existing_domain_contracts(self, relpath):
        path = _repo_root() / relpath
        source = path.read_text(encoding="utf-8")
        defined = _defined_class_names(source)
        overlap = defined & self._FORBIDDEN_CLASS_NAMES
        assert not overlap, f"{relpath} redefines existing contract(s): {overlap}"


class TestModulesImportCleanly:
    @pytest.mark.parametrize(
        "module_name",
        [
            "app.ui.dashboard_view_models",
            "app.ui.adapters.vision_adapter",
            "app.ui.adapters.ml_adapter",
            "app.ui.adapters.dl_adapter",
            "app.ui.adapters.decision_adapter",
            "app.ui.adapters.guide_adapter",
            "app.ui.adapters.navigation_adapter",
            "app.ui.adapters.speech_adapter",
            "app.ui.adapters.robot_adapter",
            "app.ui.dashboard_service",
            "app.ui.dashboard",
        ],
    )
    def test_module_imports_without_error(self, module_name):
        importlib.import_module(module_name)

    def test_existing_domain_modules_remain_importable_alongside_dashboard(self):
        # Importing the dashboard service must not break importability
        # of the existing subsystems it wraps (no circular imports).
        importlib.import_module("app.ui.dashboard_service")
        for name in (
            "app.vision", "app.ml.service", "app.dl.service",
            "app.navigation", "app.decision.state_manager",
            "app.guide", "app.speech", "app.robot", "app.integration",
        ):
            importlib.import_module(name)
