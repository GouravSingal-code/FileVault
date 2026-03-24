"""Tests for QuotaService."""
from unittest.mock import patch
from django.test import TestCase

from files.services.quota_service import QuotaService


class QuotaServiceTests(TestCase):

    def test_validate_quota_passes_when_under_limit(self):
        with patch('files.services.quota_service.StorageService.get_user_storage_usage', return_value=0):
            is_valid, msg, info = QuotaService.validate_quota('user_1', 1024, fast_mode=False)
        self.assertTrue(is_valid)
        self.assertIn('passed', msg)

    def test_validate_quota_fails_when_over_limit(self):
        # Simulate user already at quota
        quota_bytes = QuotaService._quota_bytes()
        with patch('files.services.quota_service.StorageService.get_user_storage_usage', return_value=quota_bytes):
            is_valid, msg, info = QuotaService.validate_quota('user_1', 1, fast_mode=False)
        self.assertFalse(is_valid)
        self.assertIn('quota', msg.lower())

    def test_quota_info_contains_expected_keys(self):
        with patch('files.services.quota_service.StorageService.get_user_storage_usage', return_value=0):
            _, _, info = QuotaService.validate_quota('user_1', 0, fast_mode=False)
        for key in ('quota_bytes', 'quota_mb', 'used_bytes', 'remaining_bytes', 'usage_percent'):
            self.assertIn(key, info)

    def test_usage_percent_calculated_correctly(self):
        quota_bytes = QuotaService._quota_bytes()
        half = quota_bytes // 2
        with patch('files.services.quota_service.StorageService.get_user_storage_usage', return_value=half):
            _, _, info = QuotaService.validate_quota('user_1', 0, fast_mode=False)
        self.assertAlmostEqual(info['usage_percent'], 50.0, places=1)
