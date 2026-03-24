"""Integration tests for the Kafka consumer processing flow."""
import base64
import io
from unittest.mock import patch, MagicMock
from django.test import TestCase

from files.models import UploadJob, File
from files.services.kafka_consumer import FileUploadConsumer


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')


class KafkaConsumerFlowTests(TestCase):

    def _make_job(self, user_id='consumer_user', filename='upload.txt') -> UploadJob:
        return UploadJob.objects.create(
            user_id=user_id,
            filename=filename,
            file_size=11,
            file_type='text/plain',
            status='queued',
        )

    def test_process_message_completes_job(self):
        job = self._make_job()
        consumer = FileUploadConsumer()

        message = {
            'job_id': str(job.id),
            'user_id': 'consumer_user',
            'filename': 'upload.txt',
            'file_size': 11,
            'file_type': 'text/plain',
            'file_content': _b64(b'hello world'),
        }

        consumer._process_message(message)
        job.refresh_from_db()
        self.assertEqual(job.status, 'completed')
        self.assertIsNotNone(job.file_id)

    def test_process_message_marks_duplicate(self):
        # Pre-create an original file with the same hash
        content = b'duplicate content xyz'
        from files.utils.hash_utils import compute_sha256_from_bytes
        h = compute_sha256_from_bytes(content)

        File.objects.create(
            user_id='other_user',
            original_filename='original.txt',
            file_type='text/plain',
            size=len(content),
            file_hash=h,
            is_reference=False,
            reference_count=1,
        )

        job = self._make_job(filename='copy.txt')
        consumer = FileUploadConsumer()
        message = {
            'job_id': str(job.id),
            'user_id': 'consumer_user',
            'filename': 'copy.txt',
            'file_size': len(content),
            'file_type': 'text/plain',
            'file_content': _b64(content),
        }
        consumer._process_message(message)
        job.refresh_from_db()
        self.assertEqual(job.status, 'completed')
        self.assertTrue(job.is_duplicate)

    def test_process_message_fails_gracefully_on_bad_job_id(self):
        consumer = FileUploadConsumer()
        import uuid
        message = {
            'job_id': str(uuid.uuid4()),  # does not exist
            'user_id': 'u',
            'filename': 'x.txt',
            'file_size': 0,
            'file_type': 'text/plain',
            'file_content': _b64(b''),
        }
        # Should not raise — missing job is logged and skipped
        consumer._process_message(message)
