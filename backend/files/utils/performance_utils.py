"""Performance measurement utilities."""
import time
import functools
import logging

logger = logging.getLogger('files')


def timed(label: str):
    """
    Decorator that logs the wall-clock duration of a function call.

    Usage::

        @timed('my_operation')
        def slow_function():
            ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.debug(
                    f'{label} completed',
                    extra={'event': 'performance', 'metric': label, 'value': elapsed_ms, 'unit': 'ms'},
                )
        return wrapper
    return decorator
