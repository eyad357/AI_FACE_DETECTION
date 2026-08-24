"""
Dependency isolation tests for app.dl.

Verifies, by static AST inspection (no import execution needed), that
the DL package never imports app.robot, app.vision, app.ml,
app.navigation, app.decision, app.guide, or app.main -- the
non-negotiable dependency rules from docs/contracts.md and
docs/dl.md. Also verifies the whole project still imports cleanly with
DL present (no circular imports introduced).
"""

import ast
import os

import pytest

DL_ROOT = os.path.join("app", "dl")


def _all_dl_files():
    files = []
    for dirpath, _dirnames, filenames in os.walk(DL_ROOT):
        for filename in filenames:
            if filename.endswith(".py"):
                files.append(os.path.join(dirpath, filename))
    return sorted(files)


def _imported_modules(path):
    tree = ast.parse(open(path).read())
    mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
        elif isinstance(node, ast.Import):
            mods.extend(alias.name for alias in node.names)
    return mods


class TestNoForbiddenImports:
    DL_FILES = _all_dl_files()

    def test_at_least_one_dl_file_was_discovered(self):
        # Guards against this test silently checking nothing if the
        # DL package layout ever changes.
        assert len(self.DL_FILES) >= 8

    @pytest.mark.parametrize(
        "forbidden_prefix",
        [
            "app.robot",
            "app.vision",
            "app.ml",
            "app.navigation",
            "app.decision",
            "app.guide",
            "app.main",
        ],
    )
    def test_dl_files_do_not_import_forbidden_modules(self, forbidden_prefix):
        for path in self.DL_FILES:
            mods = _imported_modules(path)
            assert not any(
                m == forbidden_prefix or m.startswith(forbidden_prefix + ".")
                for m in mods
            ), f"{path} imports forbidden module matching {forbidden_prefix}"

    def test_dl_files_do_not_import_socket_or_network_modules(self):
        forbidden = {"socket", "serial", "requests", "urllib"}
        for path in self.DL_FILES:
            mods = set(_imported_modules(path))
            assert not (mods & forbidden), f"{path} imports forbidden network module"

    def test_only_loader_imports_cv2(self):
        # OpenCV is permitted ONLY for real-dataset image-file decoding
        # in app.dl.dataset.loader (see its module docstring) -- kept
        # isolated so the rest of DL (inference/training/service) has
        # no OpenCV dependency at all.
        for path in self.DL_FILES:
            mods = set(_imported_modules(path))
            has_cv2 = any(m == "cv2" or m.startswith("cv2.") for m in mods)
            if has_cv2:
                assert path.endswith(os.path.join("dataset", "loader.py")), (
                    f"{path} imports cv2 but is not the designated dataset "
                    f"loader module"
                )


class TestNoCircularImports:
    def test_dl_modules_import_cleanly_alongside_full_project(self):
        import importlib

        for mod in (
            "app.dl",
            "app.dl.config",
            "app.dl.models",
            "app.dl.models.gesture_types",
            "app.dl.models.network",
            "app.dl.inference",
            "app.dl.inference.preprocessing",
            "app.dl.inference.engine",
            "app.dl.dataset",
            "app.dl.dataset.fixture",
            "app.dl.dataset.loader",
            "app.dl.training",
            "app.dl.training.trainer",
            "app.dl.service",
            "app.vision",
            "app.robot",
            "app.decision",
            "app.guide",
            "app.models",
            "app.config",
            "app.utils.logger",
            "app.main",
        ):
            importlib.import_module(mod)
