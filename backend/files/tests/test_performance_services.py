"""Tests for QueryOptimizer and performance_monitor."""
from django.test import TestCase

from files.models import File
from files.services.performance_services import QueryOptimizer


class QueryOptimizerTests(TestCase):

    def setUp(self):
        File.objects.create(
            user_id='perf_user',
            original_filename='report.pdf',
            file_type='application/pdf',
            size=500,
            file_hash='hash_report',
            is_reference=False,
            reference_count=1,
        )
        File.objects.create(
            user_id='perf_user',
            original_filename='image.png',
            file_type='image/png',
            size=200,
            file_hash='hash_image',
            is_reference=False,
            reference_count=1,
        )

    def test_search_filter_matches_filename(self):
        qs = File.objects.filter(user_id='perf_user')
        result = QueryOptimizer.optimize_file_search_queryset(qs, {'search': 'report'})
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().original_filename, 'report.pdf')

    def test_search_filter_case_insensitive(self):
        qs = File.objects.filter(user_id='perf_user')
        result = QueryOptimizer.optimize_file_search_queryset(qs, {'search': 'REPORT'})
        self.assertEqual(result.count(), 1)

    def test_no_filters_returns_all(self):
        qs = File.objects.filter(user_id='perf_user')
        result = QueryOptimizer.optimize_file_search_queryset(qs, {})
        self.assertEqual(result.count(), 2)

    def test_optimize_concurrent_queries_returns_queryset(self):
        qs = File.objects.filter(user_id='perf_user')
        result = QueryOptimizer.optimize_concurrent_queries(qs)
        # Should not raise and should return a valid queryset
        self.assertEqual(result.count(), 2)
