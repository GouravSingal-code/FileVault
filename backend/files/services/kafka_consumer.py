"""
Kafka consumer for async file processing.

Intended to run as a long-lived process via the Django management command
``python manage.py run_kafka_consumer``.
"""
import base64
import io
import json
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('files')


class FileUploadConsumer:
    """
    Reads messages from the file-uploads Kafka topic and processes each one:

    1. Decode base64 file content
    2. Compute SHA-256 hash
    3. Check for duplicates
    4. Save physical file or create a reference record
    5. Update UploadJob status to 'completed' or 'failed'
    """

    def __init__(self):
        self._consumer = None

    def _get_consumer(self):
        if self._consumer is not None:
            return self._consumer

        from kafka import KafkaConsumer

        self._consumer = KafkaConsumer(
            settings.KAFKA_FILE_UPLOAD_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=False,      # manual commit for at-least-once semantics
            max_poll_records=10,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )
        logger.info(
            'kafka_consumer_started',
            extra={
                'topic': settings.KAFKA_FILE_UPLOAD_TOPIC,
                'group_id': settings.KAFKA_CONSUMER_GROUP_ID,
            },
        )
        return self._consumer

    def run(self, max_messages: int | None = None) -> None:
        """
        Main consumer loop.

        Parameters
        ----------
        max_messages:
            Stop after consuming this many messages.  Useful for testing.
            ``None`` means run indefinitely.
        """
        consumer = self._get_consumer()
        count = 0

        try:
            for message in consumer:
                try:
                    self._process_message(message.value)
                    consumer.commit()
                except Exception as exc:
                    logger.error(
                        'message_processing_failed',
                        extra={'error': str(exc), 'offset': message.offset},
                    )
                    # Commit anyway so we don't block the partition; the UploadJob
                    # will already have been marked 'failed' inside _process_message.
                    consumer.commit()

                count += 1
                if max_messages is not None and count >= max_messages:
                    break
        finally:
            consumer.close()
            logger.info('kafka_consumer_stopped')

    def _process_message(self, data: dict) -> None:
        """Process a single upload message."""
        # Avoid circular imports — models are imported at call time
        from ..models import UploadJob
        from .file_services import FileHashService, DeduplicationService
        from .storage_services import StatisticsService

        job_id = data.get('job_id')
        user_id = data.get('user_id')

        try:
            job = UploadJob.objects.get(id=job_id)
        except UploadJob.DoesNotExist:
            logger.error('upload_job_not_found', extra={'job_id': job_id})
            return

        job.status = 'processing'
        job.started_at = timezone.now()
        job.save(update_fields=['status', 'started_at'])

        try:
            # Decode file content from base64
            file_content_b64 = data.get('file_content', '')
            file_bytes = base64.b64decode(file_content_b64)
            file_obj = io.BytesIO(file_bytes)

            filename = data.get('filename', 'unknown')
            file_type = data.get('file_type', 'application/octet-stream')
            file_size = data.get('file_size', len(file_bytes))

            # Compute hash
            file_hash = FileHashService.compute_hash_from_bytes(file_bytes)

            # Deduplicate / store
            # Pass file_obj only when no original exists yet to avoid redundant IO
            needs_storage = not is_duplicate_pre_check(file_hash)
            file_record, is_duplicate = DeduplicationService.get_or_create_file(
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                file_hash=file_hash,
                file_obj=file_obj if needs_storage else None,
            )

            # Update storage stats
            if not is_duplicate:
                StatisticsService.update_storage_stats_incremental(user_id, file_size, 1)
            else:
                StatisticsService.update_storage_stats_incremental(user_id, 0, 1)

            job.status = 'completed'
            job.completed_at = timezone.now()
            job.file_id = file_record.id
            job.is_duplicate = is_duplicate
            if is_duplicate and file_record.original_file:
                job.duplicate_file_id = file_record.original_file.id
            job.save(update_fields=['status', 'completed_at', 'file_id', 'is_duplicate', 'duplicate_file_id'])

            logger.info(
                'upload_job_completed',
                extra={
                    'job_id': job_id,
                    'user_id': user_id,
                    'file_id': str(file_record.id),
                    'is_duplicate': is_duplicate,
                },
            )

        except Exception as exc:
            job.status = 'failed'
            job.completed_at = timezone.now()
            job.error_message = str(exc)
            job.save(update_fields=['status', 'completed_at', 'error_message'])
            logger.error(
                'upload_job_failed',
                extra={'job_id': job_id, 'user_id': user_id, 'error': str(exc)},
            )
            raise


def is_duplicate_pre_check(file_hash: str) -> bool:
    """Quick check before acquiring locks — avoids unnecessary IO."""
    from ..models import File
    return File.objects.filter(file_hash=file_hash, is_reference=False).exists()
