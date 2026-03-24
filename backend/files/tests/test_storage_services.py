"""Tests for StorageService and StatisticsService."""
from django.test import TestCase

from files.models import File, UserStorageStats
from files.services.storage_services import StorageService, StatisticsService


class StorageServiceTests(TestCase):

    def _make_file(self, user_id, size, is_reference=False):
        return File.objects.create(
            user_id=user_id,
            original_filename='f.txt',
            file_type='text/plain',
            size=size,
            file_hash=f'hash_{user_id}_{size}_{is_reference}',
            is_reference=is_reference,
            reference_count=0 if is_reference else 1,
        )

    def test_get_user_storage_usage_counts_only_originals(self):
        self._make_file('u1', 1000, is_reference=False)
        self._make_file('u1', 500, is_reference=True)  # should NOT count
        usage = StorageService.get_user_storage_usage('u1')
        self.assertEqual(usage, 1000)

    def test_get_user_storage_usage_returns_zero_for_no_files(self):
        self.assertEqual(StorageService.get_user_storage_usage('no_files_user'), 0)


class StatisticsServiceTests(TestCase):

    def _make_file(self, user_id, size, is_reference=False, suffix=''):
        return File.objects.create(
            user_id=user_id,
            original_filename='f.txt',
            file_type='text/plain',
            size=size,
            file_hash=f'hash_{user_id}_{size}_{is_reference}_{suffix}',
            is_reference=is_reference,
            reference_count=0 if is_reference else 1,
        )

    def test_get_storage_stats_structure(self):
        self._make_file('stats_user', 2048)
        stats = StatisticsService.get_storage_stats('stats_user')
        for key in ('total_storage_used', 'file_count', 'original_files', 'reference_files'):
            self.assertIn(key, stats)

    def test_get_storage_stats_counts_files(self):
        self._make_file('count_user', 100, suffix='a')
        self._make_file('count_user', 200, suffix='b')
        stats = StatisticsService.get_storage_stats('count_user')
        self.assertEqual(stats['file_count'], 2)
        self.assertEqual(stats['original_files'], 2)

    def test_update_storage_stats_incremental(self):
        StatisticsService.update_storage_stats_incremental('inc_user', 1000, 1)
        record = UserStorageStats.objects.get(user_id='inc_user')
        self.assertEqual(record.file_count, 1)
        self.assertGreaterEqual(record.total_storage_used, 0)

    def test_update_storage_stats_does_not_go_negative(self):
        StatisticsService.update_storage_stats_incremental('neg_user', 100, 1)
        StatisticsService.update_storage_stats_incremental('neg_user', -999999, -5)
        record = UserStorageStats.objects.get(user_id='neg_user')
        self.assertGreaterEqual(record.total_storage_used, 0)
        self.assertGreaterEqual(record.file_count, 0)
