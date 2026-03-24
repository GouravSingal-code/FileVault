"""
Management command: python manage.py run_kafka_consumer

Starts the long-running Kafka consumer that processes async file uploads.
Run this in a separate process / container alongside the API server.
"""
import logging
import signal
import sys
from django.core.management.base import BaseCommand

logger = logging.getLogger('files')


class Command(BaseCommand):
    help = 'Start the Kafka consumer for async file upload processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-messages',
            type=int,
            default=None,
            help='Stop after consuming this many messages (useful for testing).',
        )

    def handle(self, *args, **options):
        from files.services.kafka_consumer import FileUploadConsumer

        consumer = FileUploadConsumer()

        # Graceful shutdown on SIGTERM / SIGINT
        def _shutdown(signum, frame):
            self.stdout.write(self.style.WARNING('\nShutting down Kafka consumer...'))
            sys.exit(0)

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)

        self.stdout.write(self.style.SUCCESS('Kafka consumer started. Waiting for messages...'))

        try:
            consumer.run(max_messages=options.get('max_messages'))
        except Exception as exc:
            logger.error('consumer_fatal_error', extra={'error': str(exc)})
            self.stderr.write(self.style.ERROR(f'Consumer failed: {exc}'))
            sys.exit(1)
