"""
Storage quota validation service.

Two modes
---------
fast_mode=True  — uses Redis (sub-millisecond; used on upload hot path)
fast_mode=False — queries the database (accurate; used for reporting)
"""
import logging
from django.conf import settings
from django.core.cache import cache

from .storage_services import StorageService

logger = logging.getLogger('files')

_QUOTA_CACHE_TTL = 60  # 1 minute


class QuotaService:

    @staticmethod
    def _quota_bytes() -> int:
        return getattr(settings, 'USER_STORAGE_QUOTA_MB', 100) * 1024 * 1024

    @staticmethod
    def _usage_cache_key(user_id: str) -> str:
        return f'storage_usage:{user_id}'

    @staticmethod
    def get_current_usage(user_id: str, fast_mode: bool = False) -> int:
        """Return current storage usage in bytes."""
        if fast_mode:
            cached = cache.get(QuotaService._usage_cache_key(user_id))
            if cached is not None:
                return int(cached)

        usage = StorageService.get_user_storage_usage(user_id)

        if fast_mode:
            cache.set(QuotaService._usage_cache_key(user_id), usage, timeout=_QUOTA_CACHE_TTL)

        return usage

    @staticmethod
    def validate_quota(
        user_id: str,
        file_size: int,
        fast_mode: bool = True,
    ) -> tuple[bool, str, dict]:
        """
        Check whether uploading `file_size` bytes would exceed the user's quota.

        Returns
        -------
        (is_valid, message, quota_info_dict)
        """
        quota = QuotaService._quota_bytes()
        current_usage = QuotaService.get_current_usage(user_id, fast_mode=fast_mode)
        remaining = max(0, quota - current_usage)

        quota_info = {
            'quota_bytes': quota,
            'quota_mb': quota / (1024 * 1024),
            'used_bytes': current_usage,
            'used_mb': round(current_usage / (1024 * 1024), 2),
            'remaining_bytes': remaining,
            'remaining_mb': round(remaining / (1024 * 1024), 2),
            'usage_percent': round((current_usage / quota) * 100, 2) if quota > 0 else 0.0,
        }

        if current_usage + file_size > quota:
            logger.warning(
                'quota_exceeded',
                extra={
                    'event': 'quota_exceeded',
                    'user_id': user_id,
                    'current_usage': current_usage,
                    'file_size': file_size,
                    'quota': quota,
                },
            )
            return (
                False,
                f'Storage quota exceeded. Available: {round(remaining / (1024 * 1024), 2)} MB.',
                quota_info,
            )

        return True, 'Quota check passed.', quota_info
