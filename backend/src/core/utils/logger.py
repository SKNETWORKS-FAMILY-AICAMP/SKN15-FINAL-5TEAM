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


class LoggerWrapper:
    """
    Wrapper that provides both function-style and method-style logging.

    Usage:
        # Function style (original)
        log("parent", "Message here")

        # Method style (standard logging)
        log.debug("Message here")
        log.info("Message here")
        log.warning("Message here")
        log.error("Message here")
    """

    def __call__(self, stage: str, message: str, *, level: int = logging.INFO, **context: Any) -> None:
        """
        Write a formatted log entry (function-style).

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

    def debug(self, message: str, **context: Any) -> None:
        """Log a DEBUG level message."""
        suffix = message
        if context:
            extras = " ".join(f"{key}={value}" for key, value in context.items())
            suffix = f"{suffix} ({extras})"
        _LOGGER.debug(suffix)

    def info(self, message: str, **context: Any) -> None:
        """Log an INFO level message."""
        suffix = message
        if context:
            extras = " ".join(f"{key}={value}" for key, value in context.items())
            suffix = f"{suffix} ({extras})"
        _LOGGER.info(suffix)

    def warning(self, message: str, **context: Any) -> None:
        """Log a WARNING level message."""
        suffix = message
        if context:
            extras = " ".join(f"{key}={value}" for key, value in context.items())
            suffix = f"{suffix} ({extras})"
        _LOGGER.warning(suffix)

    def error(self, message: str, **context: Any) -> None:
        """Log an ERROR level message."""
        suffix = message
        if context:
            extras = " ".join(f"{key}={value}" for key, value in context.items())
            suffix = f"{suffix} ({extras})"
        _LOGGER.error(suffix)

    def critical(self, message: str, **context: Any) -> None:
        """Log a CRITICAL level message."""
        suffix = message
        if context:
            extras = " ".join(f"{key}={value}" for key, value in context.items())
            suffix = f"{suffix} ({extras})"
        _LOGGER.critical(suffix)


# Create the global logger instance
log = LoggerWrapper()

__all__ = ["log"]
