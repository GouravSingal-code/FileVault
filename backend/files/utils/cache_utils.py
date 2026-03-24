"""Cache key management and invalidation helpers."""
from django.core.cache import cache

_CACHE_VERSION_TIMEOUT = 3600  # 1 hour


class CacheUtils:
    """
    Versioned cache invalidation.

    Instead of scanning for keys with a pattern (which is slow on Redis),
    we maintain a per-user, per-namespace version counter. Bumping the
    version makes all old keys effectively invisible — they will expire
    naturally at their own TTL without any explicit deletion.
    """

    @staticmethod
    def _version_key(user_id: str, namespace: str) -> str:
        return f'cache_version:{namespace}:{user_id}'

    @staticmethod
    def get_cache_version(user_id: str, namespace: str) -> int:
        key = CacheUtils._version_key(user_id, namespace)
        version = cache.get(key)
        if version is None:
            version = 1
            cache.set(key, version, timeout=_CACHE_VERSION_TIMEOUT)
        return version

    @staticmethod
    def invalidate_user_cache(user_id: str, namespace: str) -> None:
        """Bump the version so all existing cached entries for this namespace are skipped."""
        key = CacheUtils._version_key(user_id, namespace)
        try:
            cache.incr(key)
        except ValueError:
            # Key doesn't exist yet; create it
            cache.set(key, 2, timeout=_CACHE_VERSION_TIMEOUT)

    @staticmethod
    def make_key(user_id: str, namespace: str, *parts) -> str:
        """Build a versioned cache key."""
        version = CacheUtils.get_cache_version(user_id, namespace)
        suffix = ':'.join(str(p) for p in parts)
        return f'{namespace}:{user_id}:v{version}:{suffix}'
