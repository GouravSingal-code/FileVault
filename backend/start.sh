#!/bin/sh
set -e

ENVIRONMENT=${DJANGO_ENVIRONMENT:-development}
export DJANGO_SETTINGS_MODULE="core.settings.${ENVIRONMENT}"

echo "Starting File Vault — environment: ${ENVIRONMENT}"

# Ensure required directories exist
mkdir -p media/uploads logs staticfiles

# Apply migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files (required for WhiteNoise in production)
python manage.py collectstatic --noinput --clear

if [ "${ENVIRONMENT}" = "production" ]; then
    echo "Starting Gunicorn..."
    exec gunicorn core.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 4 \
        --worker-class sync \
        --worker-connections 1000 \
        --timeout 60 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --access-logfile - \
        --error-logfile - \
        --log-level info
else
    echo "Starting Django development server on http://0.0.0.0:8000/"
    exec python manage.py runserver 0.0.0.0:8000
fi
