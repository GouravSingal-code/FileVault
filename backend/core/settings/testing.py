from .base import *

DEBUG = False
ALLOWED_HOSTS = ['*']

# Use a fast in-memory SQLite database for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Use local-memory cache for tests (no Redis needed)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable Kafka during tests — services mock it
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'

# Store files in a temp directory during tests
import tempfile
MEDIA_ROOT = tempfile.mkdtemp()

# Speed up password hashing in tests
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
