"""
Health check and metrics endpoints.
"""
import time
from django.http import JsonResponse
from django.views import View
from django.core.cache import cache
from django.db import connection


class HealthCheckView(View):
    """
    GET /health/

    Returns 200 when the application and its critical dependencies are healthy.
    Returns 503 when any critical dependency is unavailable.
    """

    def get(self, request):
        checks = {}
        healthy = True

        # Database
        try:
            connection.ensure_connection()
            checks['database'] = 'ok'
        except Exception as exc:
            checks['database'] = f'error: {exc}'
            healthy = False

        # Redis / cache
        try:
            cache.set('health_check_probe', '1', timeout=5)
            assert cache.get('health_check_probe') == '1'
            checks['cache'] = 'ok'
        except Exception as exc:
            checks['cache'] = f'error: {exc}'
            # Cache failure is non-fatal — degrade gracefully
            checks['cache_warning'] = 'running without cache'

        status_code = 200 if healthy else 503
        return JsonResponse(
            {'status': 'healthy' if healthy else 'unhealthy', 'checks': checks},
            status=status_code,
        )


class MetricsView(View):
    """
    GET /metrics/

    Exposes basic application metrics in a simple JSON format.
    In production, integrate with Prometheus / Datadog instead.
    """

    def get(self, request):
        from files.models import File, UploadJob

        metrics = {}

        try:
            metrics['total_files'] = File.objects.count()
            metrics['total_upload_jobs'] = UploadJob.objects.count()
            metrics['pending_jobs'] = UploadJob.objects.filter(status='queued').count()
            metrics['failed_jobs'] = UploadJob.objects.filter(status='failed').count()
        except Exception:
            metrics['db_error'] = 'Could not query metrics'

        metrics['timestamp'] = time.time()
        return JsonResponse(metrics)
