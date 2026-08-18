"""
Centralized logging configuration for the AI University Lab Guide Robot.

Every module should obtain its logger via get_logger(__name__) instead of
using print() or configuring logging handlers itself. This keeps log
formatting and levels consistent and centrally controlled through
app.config.
"""

from __future__ import annotations

import logging

from app.config import CONFIG

_CONFIGURED = False


def _configure_root_logger() -> None:
    """Configure the root logger exactly once, using app.config values."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = CONFIG.logging.level.upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(CONFIG.logging.format))

    root = logging.getLogger("labguide")
    root.setLevel(level)
    # Avoid attaching duplicate handlers if this is called more than once
    # (e.g. in tests that import several modules).
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
    root.propagate = False

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a namespaced logger under the shared "labguide" root logger.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A configured logging.Logger instance.
    """
    _configure_root_logger()
    return logging.getLogger(f"labguide.{name}")
