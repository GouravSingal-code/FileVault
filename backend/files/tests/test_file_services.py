"""Tests for FileHashService and DeduplicationService."""
import io
from unittest.mock import patch, MagicMock
from django.test import TestCase

from files.services.file_services import FileHashService, DeduplicationService
from files.models import File


class FileHashServiceTests(TestCase):

    def test_compute_hash_returns_64_char_hex(self):
        data = b'hello world'
        file_obj = io.BytesIO(data)
        result = FileHashService.compute_hash(file_obj)
        self.assertEqual(len(result), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in result))

    def test_compute_hash_is_deterministic(self):
        data = b'deterministic content'
        h1 = FileHashService.compute_hash(io.BytesIO(data))
        h2 = FileHashService.compute_hash(io.BytesIO(data))
        self.assertEqual(h1, h2)

    def test_compute_hash_differs_for_different_content(self):
        h1 = FileHashService.compute_hash(io.BytesIO(b'content A'))
        h2 = FileHashService.compute_hash(io.BytesIO(b'content B'))
        self.assertNotEqual(h1, h2)

    def test_compute_hash_from_bytes(self):
        data = b'bytes test'
        h1 = FileHashService.compute_hash(io.BytesIO(data))
        h2 = FileHashService.compute_hash_from_bytes(data)
        self.assertEqual(h1, h2)


class DeduplicationServiceTests(TestCase):

    def _make_file(self, user_id='user_1', filename='test.txt', file_hash='abc123'):
        return File.objects.create(
            user_id=user_id,
            original_filename=filename,
            file_type='text/plain',
            size=100,
            file_hash=file_hash,
            is_reference=False,
            reference_count=1,
        )

    def test_find_original_returns_none_when_no_match(self):
        result = DeduplicationService.find_original('nonexistent_hash')
        self.assertIsNone(result)

    def test_find_original_returns_non_reference_file(self):
        original = self._make_file(file_hash='hash_xyz')
        result = DeduplicationService.find_original('hash_xyz')
        self.assertEqual(result.id, original.id)

    def test_get_or_create_file_creates_original_on_first_upload(self):
        file_obj = io.BytesIO(b'unique content for test')
        _, is_dup = DeduplicationService.get_or_create_file(
            user_id='user_1',
            filename='unique.txt',
            file_type='text/plain',
            file_size=23,
            file_hash='unique_hash_001',
            file_obj=file_obj,
        )
        self.assertFalse(is_dup)
        self.assertEqual(File.objects.filter(file_hash='unique_hash_001').count(), 1)

    def test_get_or_create_file_creates_reference_on_duplicate(self):
        # First upload
        original_file = self._make_file(file_hash='dup_hash_001')

        # Second upload with same hash
        ref, is_dup = DeduplicationService.get_or_create_file(
            user_id='user_2',
            filename='copy.txt',
            file_type='text/plain',
            file_size=100,
            file_hash='dup_hash_001',
        )
        self.assertTrue(is_dup)
        self.assertTrue(ref.is_reference)
        self.assertEqual(ref.original_file.id, original_file.id)

    def test_reference_count_incremented_on_duplicate(self):
        original = self._make_file(file_hash='ref_count_hash')
        initial_count = original.reference_count

        DeduplicationService.get_or_create_file(
            user_id='user_2',
            filename='dup.txt',
            file_type='text/plain',
            file_size=100,
            file_hash='ref_count_hash',
        )

        original.refresh_from_db()
        self.assertEqual(original.reference_count, initial_count + 1)
