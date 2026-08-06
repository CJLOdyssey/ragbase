"""Centralized logging configuration with JSON formatting support."""

import json
import logging
import os
import sys


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """Get or create a configured logger with optional observability handler."""
    logger = _get_logger(name, level)
    _maybe_attach_obs_handler(logger)
    return logger


def _get_logger(name: str, level: int | None = None) -> logging.Logger:
    """Get a logger with consistent formatting for the backend package.

    Usage:
        logger = get_logger(__name__)
        logger.info("...")
        logger.error("...", exc_info=True)

    Log format is controlled by the LOG_FORMAT environment variable:
      - "json"  → structured JSON lines (for log aggregators like Loki/ELK)
      - default → human-readable plaintext with timestamps
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    log_format = os.environ.get("LOG_FORMAT", "text").lower()
    handler = _json_handler() if log_format == "json" else _text_handler()

    if level is not None:
        logger.setLevel(level)
    else:
        logger.setLevel(logging.DEBUG if _is_debug() else logging.INFO)

    logger.addHandler(handler)
    logger.propagate = False
    _maybe_attach_obs_handler(logger)
    return logger


class JsonFormatter(logging.Formatter):
    """JSON log formatter for integration with log aggregators (Loki/ELK)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        try:
            message = record.getMessage()
        except (TypeError, ValueError):
            message = record.msg
        return json.dumps(
            {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": message,
                "module": record.module,
                "line": record.lineno,
            },
            ensure_ascii=False,
        )


def _text_handler() -> logging.Handler:
    """Create a human-readable text log handler writing to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)-5s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    return handler


def _json_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    return handler


def _is_debug() -> bool:
    return os.environ.get("LOG_LEVEL", "").upper() == "DEBUG"


_OBS_ATTACHED = False


_OBS_HANDLER: logging.Handler | None = None


def _maybe_attach_obs_handler(logger: logging.Logger) -> None:
    global _OBS_HANDLER
    if os.environ.get("OBSERVABILITY_ENABLED", "1") == "0":
        return
    try:
        from observability.handler import ObservabilityHandler
        if _OBS_HANDLER is None:
            _OBS_HANDLER = ObservabilityHandler()
        if _OBS_HANDLER not in logger.handlers:
            logger.addHandler(_OBS_HANDLER)
    except Exception:
        pass
