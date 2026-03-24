"""
Query optimisation and performance monitoring utilities.
"""
import functools
import time
import logging
from django.db.models import QuerySet

logger = logging.getLogger('files')


def performance_monitor(operation_name: str):
    """
    Method decorator that times a ViewSet action and logs the duration.

    Usage::

        @performance_monitor('file_list_api')
        def list(self, request, *args, **kwargs):
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
                    f'{operation_name} completed in {elapsed_ms:.1f}ms',
                    extra={
                        'event': 'performance',
                        'metric': operation_name,
                        'value': elapsed_ms,
                        'unit': 'ms',
                    },
                )
        return wrapper
    return decorator


class QueryOptimizer:
    """
    Applies search / filter conditions to a File queryset efficiently.
    """

    @staticmethod
    def optimize_file_search_queryset(queryset: QuerySet, filters: dict) -> QuerySet:
        """
        Apply text-search and date-range filters.

        ``file_type``, ``min_size``, and ``max_size`` are intentionally
        left to the caller so this method stays focused on its own concerns.
        """
        search = filters.get('search')
        if search:
            queryset = queryset.filter(original_filename__icontains=search)

        start_date = filters.get('start_date')
        if start_date:
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(start_date)
            if parsed:
                queryset = queryset.filter(uploaded_at__gte=parsed)

        end_date = filters.get('end_date')
        if end_date:
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(end_date)
            if parsed:
                queryset = queryset.filter(uploaded_at__lte=parsed)

        return queryset

    @staticmethod
    def optimize_concurrent_queries(queryset: QuerySet) -> QuerySet:
        """
        Apply queryset-level hints to reduce per-row overhead.

        In practice this is a no-op placeholder — real concurrency
        optimisations (connection pooling, read replicas) live at the
        infrastructure layer.
        """
        return queryset
