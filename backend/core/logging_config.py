"""
Structured logging helpers for the File Vault application.

All log calls go through these helpers so every log entry carries consistent
context fields that can be parsed by log aggregators (Datadog, ELK, etc.).
"""
import logging
import traceback
from typing import Any

logger = logging.getLogger('files')


def log_request(request) -> None:
    """Log an inbound HTTP request with user context."""
    user_id = getattr(request, 'user_id', 'anonymous')
    logger.info(
        'request',
        extra={
            'event': 'http_request',
            'method': request.method,
            'path': request.path,
            'user_id': user_id,
            'content_type': request.content_type,
        },
    )


def log_file_operation(operation: str, user_id: str, file_id: Any, extra: dict | None = None) -> None:
    """Log a file-level operation (upload, delete, access, …)."""
    logger.info(
        operation,
        extra={
            'event': 'file_operation',
            'operation': operation,
            'user_id': user_id,
            'file_id': str(file_id),
            **(extra or {}),
        },
    )


def log_error(error: Any, context: dict | None = None) -> None:
    """Log an error with optional context dict and stack trace."""
    ctx = context or {}
    if isinstance(error, Exception):
        logger.error(
            str(error),
            extra={
                'event': 'error',
                'error_type': type(error).__name__,
                'traceback': traceback.format_exc(),
                **ctx,
            },
        )
    else:
        logger.error(
            str(error),
            extra={'event': 'error', **ctx},
        )


def log_security_event(event: str, user_id: str, extra: dict | None = None) -> None:
    """Log a security-relevant event (unauthorized access, quota exceeded, …)."""
    logger.warning(
        event,
        extra={
            'event': 'security',
            'security_event': event,
            'user_id': user_id,
            **(extra or {}),
        },
    )


def log_performance_metric(metric: str, value: Any = None, unit: str = '', extra: dict | None = None) -> None:
    """Log a performance metric (duration, cache hit/miss, …)."""
    logger.debug(
        metric,
        extra={
            'event': 'performance',
            'metric': metric,
            'value': value,
            'unit': unit,
            **(extra or {}),
        },
    )
