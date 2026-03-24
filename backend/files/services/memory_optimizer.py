"""
Optional cache compression utilities.

Compressing large cached values with zlib reduces Redis memory usage at the
cost of a small CPU overhead on cache reads/writes. Enable selectively for
large payloads (e.g. serialized file-list responses).
"""
import zlib
import json
import logging
from django.core.cache import cache

logger = logging.getLogger('files')

_COMPRESSION_THRESHOLD = 1024  # bytes — only compress values larger than 1 KB


class CacheCompressionService:

    @staticmethod
    def set_compressed_cache(key: str, value, timeout: int = 300) -> bool:
        """
        Serialize `value` to JSON, optionally compress it, and store in cache.

        Returns True on success, False on any error (fail-open).
        """
        try:
            raw = json.dumps(value).encode('utf-8')
            if len(raw) > _COMPRESSION_THRESHOLD:
                payload = zlib.compress(raw, level=6)
                cache.set(f'compressed:{key}', payload, timeout=timeout)
                cache.set(f'compressed_flag:{key}', True, timeout=timeout)
            else:
                cache.set(key, value, timeout=timeout)
            return True
        except Exception as exc:
            logger.warning('cache_compression_failed', extra={'key': key, 'error': str(exc)})
            return False

    @staticmethod
    def get_compressed_cache(key: str):
        """
        Retrieve and decompress a value previously stored by set_compressed_cache.

        Returns None on cache miss or any error.
        """
        try:
            if cache.get(f'compressed_flag:{key}'):
                payload = cache.get(f'compressed:{key}')
                if payload is None:
                    return None
                raw = zlib.decompress(payload)
                return json.loads(raw.decode('utf-8'))
            return cache.get(key)
        except Exception as exc:
            logger.warning('cache_decompression_failed', extra={'key': key, 'error': str(exc)})
            return None
