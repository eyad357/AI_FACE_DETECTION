"""
Module isolation tests for app.speech.

Verifies (statically, via AST inspection of the actual source files --
not just "it happened to work at runtime") that the Speech &
Conversation layer never imports app.robot, app.ml, app.vision,
app.dl, or app.main, per the phase's dependency rules (see
app/speech/__init__.py). Also verifies there is no network dependency
and that RobotCommandType is never referenced.
"""

import ast
import importlib
import sys
from pathlib import Path

import pytest

SPEECH_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "app" / "speech"

FORBIDDEN_MODULE_PREFIXES = (
    "app.robot",
    "app.ml",
    "app.vision",
    "app.dl",
    "app.main",
)

# No Speech module should need network/socket access -- it is fully
# offline/local per the phase instructions.
FORBIDDEN_NETWORK_MODULES = ("requests", "urllib", "socket", "http.client")


def _speech_source_files():
    assert SPEECH_PACKAGE_DIR.is_dir(), "app/speech package not found"
    return sorted(SPEECH_PACKAGE_DIR.glob("*.py"))


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


class TestNoForbiddenImports:
    @pytest.mark.parametrize("path", _speech_source_files(), ids=lambda p: p.name)
    def test_file_has_no_forbidden_imports(self, path):
        source = path.read_text(encoding="utf-8")
        imported = _imported_module_names(source)
        for module_name in imported:
            for forbidden in FORBIDDEN_MODULE_PREFIXES:
                assert not (
                    module_name == forbidden or module_name.startswith(forbidden + ".")
                ), f"{path.name} imports forbidden module: {module_name}"

    @pytest.mark.parametrize("path", _speech_source_files(), ids=lambda p: p.name)
    def test_file_has_no_network_imports(self, path):
        source = path.read_text(encoding="utf-8")
        imported = _imported_module_names(source)
        for module_name in imported:
            for forbidden in FORBIDDEN_NETWORK_MODULES:
                assert not module_name.startswith(forbidden), (
                    f"{path.name} imports network module: {module_name}"
                )

    def test_no_robot_command_type_reference_anywhere_in_package(self):
        # Checked via AST identifiers (Name/Attribute nodes), not raw
        # substring search, so explanatory prose in docstrings (e.g.
        # "this module must never modify RobotCommandType") does not
        # produce a false positive -- only actual code use would.
        forbidden_identifiers = {"RobotCommandType", "RobotCommand"}
        for path in _speech_source_files():
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    assert node.id not in forbidden_identifiers, (
                        f"{path.name} references {node.id} as code, which "
                        "app.speech must never create or modify"
                    )
                if isinstance(node, ast.Attribute):
                    assert node.attr not in forbidden_identifiers, (
                        f"{path.name} references {node.attr} as code, which "
                        "app.speech must never create or modify"
                    )


class TestNoRobotDependencyAtRuntime:
    def test_app_robot_not_imported_as_a_side_effect(self):
        # Reload app.speech in isolation and confirm app.robot was not
        # pulled in as a transitive import.
        for name in list(sys.modules):
            if name == "app.robot" or name.startswith("app.robot."):
                del sys.modules[name]

        importlib.import_module("app.speech")

        assert not any(
            name == "app.robot" or name.startswith("app.robot.")
            for name in sys.modules
        ), "app.speech import pulled in app.robot as a side effect"


class TestNoMLDependencyAtRuntime:
    def test_app_ml_not_imported_as_a_side_effect(self):
        for name in list(sys.modules):
            if name == "app.ml" or name.startswith("app.ml."):
                del sys.modules[name]

        importlib.import_module("app.speech")

        assert not any(
            name == "app.ml" or name.startswith("app.ml.")
            for name in sys.modules
        ), "app.speech import pulled in app.ml as a side effect"


class TestOfflineDeterministicBehavior:
    def test_same_input_yields_same_output(self):
        from app.speech import ConversationInput, ConversationService

        service = ConversationService()
        first = service.handle(ConversationInput(text="Where is the AI Lab?"))
        second = service.handle(ConversationInput(text="Where is the AI Lab?"))
        assert first.spoken_text == second.spoken_text
        assert first.response_type == second.response_type
