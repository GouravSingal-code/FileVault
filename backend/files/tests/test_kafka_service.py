"""Tests for KafkaService (producer side) using mocks."""
from unittest.mock import patch, MagicMock
from django.test import TestCase

from files.services.kafka_service import KafkaService


class KafkaServiceTests(TestCase):

    def setUp(self):
        # Reset singleton producer between tests
        KafkaService._producer = None

    def test_send_upload_request_returns_true_on_success(self):
        mock_future = MagicMock()
        mock_future.get.return_value = MagicMock(topic='file-uploads', partition=0, offset=1)

        mock_producer = MagicMock()
        mock_producer.send.return_value = mock_future

        with patch.object(KafkaService, '_get_producer', return_value=mock_producer):
            result = KafkaService.send_upload_request(
                job_id='job-123',
                user_id='user_1',
                file_data={
                    'filename': 'test.txt',
                    'file_size': 100,
                    'file_type': 'text/plain',
                    'file_content': 'aGVsbG8=',
                },
            )
        self.assertTrue(result)

    def test_send_upload_request_raises_on_kafka_error(self):
        with patch.object(KafkaService, '_get_producer', side_effect=Exception('broker down')):
            with self.assertRaises(Exception):
                KafkaService.send_upload_request(
                    job_id='job-456',
                    user_id='user_1',
                    file_data={'filename': 'f.txt', 'file_size': 1, 'file_type': 'text/plain', 'file_content': ''},
                )

    def test_producer_singleton_reused(self):
        mock_future = MagicMock()
        mock_future.get.return_value = MagicMock(topic='file-uploads', partition=0, offset=0)
        mock_producer = MagicMock()
        mock_producer.send.return_value = mock_future

        with patch('files.services.kafka_service.KafkaProducer', return_value=mock_producer) as mock_cls:
            KafkaService._producer = None
            KafkaService._get_producer()
            KafkaService._get_producer()
            # Constructor should only be called once
            mock_cls.assert_called_once()
