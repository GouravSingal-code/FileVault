from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# Development-only apps
INSTALLED_APPS += ['django.contrib.staticfiles']

# Relax security for local development
CORS_ALLOW_ALL_ORIGINS = True
