from __future__ import annotations

import logging
from typing import Any

_LOGGER_NAME = "story_engine"
_LOGGER = logging.getLogger(_LOGGER_NAME)

if not _LOGGER.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    _LOGGER.addHandler(handler)
    _LOGGER.propagate = False

_LOGGER.setLevel(logging.INFO)


def log(stage: str, message: str, *, level: int = logging.INFO, **context: Any) -> None:
    """
    Write a formatted log entry.

    Args:
        stage: Logical stage name for the log prefix.
        message: Human readable log message.
        level: Standard logging level (INFO by default).
        context: Optional key/value metadata to append for quick scanning.
    """
    prefix = stage.upper() if stage else "GENERAL"
    suffix = message
    if context:
        extras = " ".join(f"{key}={value}" for key, value in context.items())
        suffix = f"{suffix} ({extras})"
    _LOGGER.log(level, f"[{prefix}] {suffix}")


__all__ = ["log"]
