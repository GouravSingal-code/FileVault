"""
Kafka producer service for async file upload requests.
"""
import json
import logging
from django.conf import settings

logger = logging.getLogger('files')


class KafkaService:
    """
    Wraps kafka-python's KafkaProducer.

    Lazy initialisation: the producer is created on first use and reused
    for subsequent calls. If Kafka is unavailable the service logs the error
    and returns False so the caller can mark the job as failed gracefully.
    """

    _producer = None

    @classmethod
    def _get_producer(cls):
        if cls._producer is not None:
            return cls._producer

        from kafka import KafkaProducer
        from kafka.errors import NoBrokersAvailable

        try:
            cls._producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',               # wait for all in-sync replicas
                retries=3,
                max_block_ms=5000,        # fail fast if broker unreachable
                request_timeout_ms=10000,
            )
            logger.info('kafka_producer_connected', extra={'servers': settings.KAFKA_BOOTSTRAP_SERVERS})
        except NoBrokersAvailable as exc:
            logger.error('kafka_no_brokers', extra={'error': str(exc)})
            raise

        return cls._producer

    @classmethod
    def send_upload_request(
        cls,
        job_id: str,
        user_id: str,
        file_data: dict,
        optimized: bool = True,
    ) -> bool:
        """
        Send a file upload message to the configured Kafka topic.

        Parameters
        ----------
        job_id:    UUID string of the UploadJob record
        user_id:   Uploader's user ID (used as message key for ordering)
        file_data: Dict with keys filename, file_size, file_type, file_content
        optimized: When True the user_id is used as the partition key so all
                   uploads from the same user land on the same partition.

        Returns True on success, False on any error.
        """
        topic = settings.KAFKA_FILE_UPLOAD_TOPIC
        message = {
            'job_id': job_id,
            'user_id': user_id,
            **file_data,
        }
        key = user_id if optimized else job_id

        try:
            producer = cls._get_producer()
            future = producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=10)

            logger.info(
                'kafka_message_sent',
                extra={
                    'event': 'kafka',
                    'job_id': job_id,
                    'user_id': user_id,
                    'topic': record_metadata.topic,
                    'partition': record_metadata.partition,
                    'offset': record_metadata.offset,
                },
            )
            return True

        except Exception as exc:
            # Reset producer so next call reconnects
            cls._producer = None
            logger.error(
                'kafka_send_failed',
                extra={
                    'event': 'kafka_error',
                    'job_id': job_id,
                    'user_id': user_id,
                    'error': str(exc),
                },
            )
            raise
