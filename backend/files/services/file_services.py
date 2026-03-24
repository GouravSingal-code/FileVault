"""
File hashing and deduplication services.
"""
import logging
from django.db import transaction

from ..utils.hash_utils import compute_sha256, compute_sha256_from_bytes
from ..models import File

logger = logging.getLogger('files')


class FileHashService:
    """Compute and cache SHA-256 hashes for uploaded files."""

    @staticmethod
    def compute_hash(file_obj) -> str:
        """Return the SHA-256 hex digest of a Django UploadedFile."""
        return compute_sha256(file_obj)

    @staticmethod
    def compute_hash_from_bytes(data: bytes) -> str:
        """Return the SHA-256 hex digest of raw bytes."""
        return compute_sha256_from_bytes(data)


class DeduplicationService:
    """
    Cross-user file deduplication via SHA-256 content hashing.

    Algorithm
    ---------
    1. Look up an existing *original* (non-reference) File with the same hash.
    2. If found → create a reference record (no physical file stored).
    3. If not found → save the physical file and create an original record.
    """

    @staticmethod
    def find_original(file_hash: str) -> File | None:
        """
        Return the canonical (non-reference) File for a given hash, or None.
        Uses select_for_update so the caller can safely increment reference_count.
        Must be called inside a transaction.
        """
        return (
            File.objects.filter(file_hash=file_hash, is_reference=False)
            .select_for_update()
            .first()
        )

    @staticmethod
    @transaction.atomic
    def get_or_create_file(
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        file_hash: str,
        file_obj=None,
    ) -> tuple[File, bool]:
        """
        Return (file_instance, is_duplicate).

        If a file with the same hash already exists the new record is created
        as a reference pointing to the original — no physical storage is used.
        """
        original = DeduplicationService.find_original(file_hash)

        if original:
            # Duplicate detected — create a reference entry
            reference = File.objects.create(
                user_id=user_id,
                original_filename=filename,
                file_type=file_type,
                size=file_size,
                file_hash=file_hash,
                is_reference=True,
                original_file=original,
                reference_count=0,
            )
            original.reference_count += 1
            original.save(update_fields=['reference_count'])

            logger.info(
                'deduplication_reference_created',
                extra={
                    'event': 'deduplication',
                    'user_id': user_id,
                    'original_file_id': str(original.id),
                    'reference_file_id': str(reference.id),
                    'filename': filename,
                },
            )
            return reference, True

        # Unique file — store physically and create original record
        new_file = File(
            user_id=user_id,
            original_filename=filename,
            file_type=file_type,
            size=file_size,
            file_hash=file_hash,
            is_reference=False,
            reference_count=1,
        )
        if file_obj is not None:
            new_file.file.save(filename, file_obj, save=False)
        new_file.save()

        logger.info(
            'file_created',
            extra={
                'event': 'file_created',
                'user_id': user_id,
                'file_id': str(new_file.id),
                'filename': filename,
                'size': file_size,
            },
        )
        return new_file, False
